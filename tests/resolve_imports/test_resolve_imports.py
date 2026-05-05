"""
Testes para compiler/resolve_imports.py.

Cobre:
  - Resolução básica de um proc-bloco importado
  - Importação de múltiplos nomes
  - Vírgula final opcional
  - Arquivo externo não encontrado → ResolveImportError
  - Nome não existente no arquivo externo → ResolveImportError
  - Conflito de nome com proc local → ResolveImportError
  - Importação circular → ResolveImportError
  - Importação em cadeia (A importa B que importa C)
"""

import textwrap
from pathlib import Path

import pytest

from compiler.parser import parse, ProcBlockNode, ProcDeclNode, ProcImportNode
from compiler.resolve_imports import resolve_imports, ResolveImportError


# ---------------------------------------------------------------------------
# Fixtures: conteúdo de arquivos .gnj externos
# ---------------------------------------------------------------------------

# Arquivo "utils.gnj" — contém dois proc-blocos exportáveis
UTILS_GNJ = textwrap.dedent('''\
program "utils"
vars {}
procs {
    NotificaErro(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    Avisa(msg: Text) {
        exec NotificaErro(msg=msg) as "Avisa" {
            pass REINICIAR
        }
    }
    TrocaFerramenta(slot: Number) {
        exec NotificaErro(msg="trocando") as "Troca" {
            pass REINICIAR
        }
    }
}
exec NotificaErro(msg="boot") as "Boot" {
    pass REINICIAR
}
''')

# Arquivo "base.gnj" — importa proc de utils.gnj (cadeia)
BASE_GNJ = textwrap.dedent('''\
program "base"
vars {}
procs {
    NotificaErro(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    from "utils" import
        Avisa
    Local(x: Number) {
        exec NotificaErro(msg="local") as "Local" {
            pass REINICIAR
        }
    }
}
exec NotificaErro(msg="init") as "Init" {
    pass REINICIAR
}
''')


# Programa importador básico
def _make_importer(import_line: str) -> str:
    return textwrap.dedent(f'''\
program "importador"
vars {{}}
procs {{
    NotificaErro(msg: Text) from "Lib.notif" {{
        codes REINICIAR<99>
    }}
    {import_line}
}}
exec NotificaErro(msg="inicio") as "Inicio" {{
    pass REINICIAR
}}
''')


# ---------------------------------------------------------------------------
# Helper: tmpdir com arquivo externo
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / f"{name}.gnj"
    f.write_text(content, encoding='utf-8')
    return f


# ---------------------------------------------------------------------------
# Testes de resolução bem-sucedida
# ---------------------------------------------------------------------------

class TestResolveSuccess:
    def test_single_import_replaces_import_node(self, tmp_path):
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = _make_importer('from "utils" import\n    Avisa')
        ast = parse(src)
        # Antes da resolução, deve conter ProcImportNode
        assert any(isinstance(p, ProcImportNode) for p in ast.procedures)

        resolved = resolve_imports(ast, base_dir=tmp_path)
        # Após resolução, nenhum ProcImportNode
        assert not any(isinstance(p, ProcImportNode) for p in resolved.procedures)
        names = [p.name for p in resolved.procedures if isinstance(p, ProcBlockNode)]
        assert 'Avisa' in names

    def test_multiple_imports(self, tmp_path):
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = _make_importer('from "utils" import\n    Avisa,\n    TrocaFerramenta')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures if isinstance(p, ProcBlockNode)]
        assert 'Avisa' in names
        assert 'TrocaFerramenta' in names

    def test_trailing_comma_accepted(self, tmp_path):
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = _make_importer('from "utils" import\n    Avisa,')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures if isinstance(p, ProcBlockNode)]
        assert 'Avisa' in names

    def test_import_chain(self, tmp_path):
        """A importa B que importa C — deve resolver em cadeia."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        _write(tmp_path, 'base', BASE_GNJ)
        src = _make_importer('from "base" import\n    Local')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures if isinstance(p, ProcBlockNode)]
        assert 'Local' in names

    def test_no_import_nodes_unchanged(self, tmp_path):
        """Programa sem import não é alterado."""
        src = textwrap.dedent('''\
program "p"
vars {}
procs {
    Foo() from "A.B" {
        codes OK<0>
    }
}
exec Foo() as "X" {
    pass OK
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        assert resolved.procedures == ast.procedures


# ---------------------------------------------------------------------------
# Testes de erro
# ---------------------------------------------------------------------------

class TestResolveErrors:
    def test_file_not_found(self, tmp_path):
        src = _make_importer('from "nao_existe" import\n    Avisa')
        ast = parse(src)
        with pytest.raises(ResolveImportError, match="não encontrado"):
            resolve_imports(ast, base_dir=tmp_path)

    def test_name_not_in_external(self, tmp_path):
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = _make_importer('from "utils" import\n    NaoExiste')
        ast = parse(src)
        with pytest.raises(ResolveImportError, match="não encontrado"):
            resolve_imports(ast, base_dir=tmp_path)

    def test_name_conflict_with_local(self, tmp_path):
        _write(tmp_path, 'utils', UTILS_GNJ)
        # "NotificaErro" é um ProcDeclNode local — importar proc-bloco com mesmo nome é conflito
        # TrocaFerramenta existe no externo mas vamos criar conflito via proc-bloco local
        conflict_gnj = textwrap.dedent('''\
program "conflict"
vars {}
procs {
    Notif(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    Avisa(msg: Text) {
        exec Notif(msg=msg) as "Avisa" {
            pass REINICIAR
        }
    }
}
exec Notif(msg="x") as "X" {
    pass REINICIAR
}
''')
        _write(tmp_path, 'conflict', conflict_gnj)
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    NotificaErro(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    Avisa(msg: Text) {
        exec NotificaErro(msg=msg) as "Avisa" {
            pass REINICIAR
        }
    }
    from "conflict" import
        Avisa
}
exec NotificaErro(msg="inicio") as "Inicio" {
    pass REINICIAR
}
''')
        ast = parse(src)
        with pytest.raises(ResolveImportError, match="conflito"):
            resolve_imports(ast, base_dir=tmp_path)

    def test_circular_import(self, tmp_path):
        """A importa B que importa A — deve detectar ciclo."""
        a_gnj = textwrap.dedent('''\
program "a"
vars {}
procs {
    Foo() from "Lib.x" {
        codes OK<0>
    }
    from "b" import
        Bar
}
exec Foo() as "X" {
    pass OK
}
''')
        b_gnj = textwrap.dedent('''\
program "b"
vars {}
procs {
    Foo() from "Lib.x" {
        codes OK<0>
    }
    from "a" import
        Something
}
exec Foo() as "X" {
    pass OK
}
''')
        _write(tmp_path, 'a', a_gnj)
        _write(tmp_path, 'b', b_gnj)
        ast_a = parse(a_gnj)
        with pytest.raises(ResolveImportError, match="circular"):
            resolve_imports(ast_a, base_dir=tmp_path)


# ---------------------------------------------------------------------------
# Testes de injeção automática de dependências (B-030)
# ---------------------------------------------------------------------------

class TestDependencyInjection:
    def test_procdecl_dep_is_injected(self, tmp_path):
        """Importar proc-bloco injeta automaticamente os ProcDeclNode dos quais depende."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        # Avisa depende de NotificaErro (ProcDeclNode) — não declarado localmente
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    Dummy() from "Lib.dummy" {
        codes OK<0>
    }
    from "utils" import
        Avisa
}
exec Dummy() as "X" {
    pass OK
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures]
        assert 'Avisa' in names
        assert 'NotificaErro' in names  # injetado automaticamente

    def test_procdecl_dep_already_local_is_skipped(self, tmp_path):
        """Dep já declarada localmente (mesma definição) não gera conflito nem duplicata."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    NotificaErro(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    from "utils" import
        Avisa
}
exec NotificaErro(msg="x") as "X" {
    pass REINICIAR
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures]
        assert 'Avisa' in names
        assert 'NotificaErro' in names
        # Não duplicado
        assert names.count('NotificaErro') == 1

    def test_explicit_procdecl_import(self, tmp_path):
        """Import explícito de ProcDeclNode deve funcionar."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    Dummy() from "Lib.dummy" {
        codes OK<0>
    }
    from "utils" import
        NotificaErro
}
exec Dummy() as "X" {
    pass OK
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures]
        assert 'NotificaErro' in names
        assert isinstance(next(p for p in resolved.procedures if p.name == 'NotificaErro'), ProcDeclNode)

    def test_mixed_explicit_import(self, tmp_path):
        """Import explícito misto: ProcDecl + ProcBlock no mesmo statement."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    Dummy() from "Lib.dummy" {
        codes OK<0>
    }
    from "utils" import
        NotificaErro,
        Avisa
}
exec Dummy() as "X" {
    pass OK
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures]
        assert 'NotificaErro' in names
        assert 'Avisa' in names
        # NotificaErro não duplicado (importado explicitamente + seria dep de Avisa)
        assert names.count('NotificaErro') == 1

    def test_transitive_procblock_dep_injected(self, tmp_path):
        """Proc-bloco que depende de outro proc-bloco: dependência transitiva injetada."""
        outer_gnj = textwrap.dedent('''\
program "outer"
vars {}
procs {
    Base() from "Lib.base" {
        codes OK<0>
    }
    Inner() {
        exec Base() as "Inner" {
            pass OK
        }
    }
    Outer() {
        exec Inner() as "Outer" {
            pass OK
        }
    }
}
exec Base() as "X" {
    pass OK
}
''')
        _write(tmp_path, 'outer', outer_gnj)
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    Dummy() from "Lib.dummy" {
        codes OK<0>
    }
    from "outer" import
        Outer
}
exec Dummy() as "X" {
    pass OK
}
''')
        ast = parse(src)
        resolved = resolve_imports(ast, base_dir=tmp_path)
        names = [p.name for p in resolved.procedures]
        assert 'Outer' in names
        assert 'Inner' in names   # dep transitiva de Outer
        assert 'Base' in names    # dep transitiva de Inner

    def test_dep_conflict_with_local_raises(self, tmp_path):
        """Dep injetada com definição diferente da local → ResolveImportError (conflito)."""
        _write(tmp_path, 'utils', UTILS_GNJ)
        # Declara NotificaErro localmente com lib diferente da versão em utils.gnj
        src = textwrap.dedent('''\
program "importador"
vars {}
procs {
    NotificaErro(msg: Text) from "Lib.OUTRA_LIB" {
        codes REINICIAR<99>
    }
    Dummy() from "Lib.dummy" {
        codes OK<0>
    }
    from "utils" import
        Avisa
}
exec Dummy() as "X" {
    pass OK
}
''')
        ast = parse(src)
        with pytest.raises(ResolveImportError, match="conflito"):
            resolve_imports(ast, base_dir=tmp_path)
