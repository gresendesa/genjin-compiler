"""
Testes de integração para B-031: API pública do compilador com resolvedores customizados.

Cobre:
  - compile_gnj() com resolver padrão (filesystem via base_dir)
  - compile_gnj() com GnjSourceResolver customizado (in-memory)
  - resolve_imports() com gnj_resolver customizado (in-memory)
  - assembler.render() com loader customizado (DictLoader)
  - CompilerConfig: campos acessíveis e valores padrão
  - FilesystemGnjResolver: comportamento filesystem
"""

import textwrap
from pathlib import Path

import pytest
from jinja2 import DictLoader

from compiler import compile_gnj, CompilerConfig, FilesystemGnjResolver, GnjSourceResolver
from compiler.resolve_imports import resolve_imports, ResolveImportError
from compiler.parser import parse
from assembler import render, DottedLoader


# ---------------------------------------------------------------------------
# Programa Genjin mínimo para testes
# ---------------------------------------------------------------------------

_MINIMAL_GNJ = textwrap.dedent("""\
program "test"
vars {}
procs {
    Ping() from "Lib.ping" {
        codes OK<0>
    }
}
exec Ping() as "Pinga" {
    pass OK
}
""")

# Proc-bloco em arquivo externo para testes de import customizado
_EXTERNAL_GNJ = textwrap.dedent("""\
program "external"
vars {}
procs {
    Notifica(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    Avisa(msg: Text) {
        exec Notifica(msg=msg) as "Avisa" {
            pass REINICIAR
        }
    }
}
exec Notifica(msg="boot") as "Boot" {
    pass REINICIAR
}
""")

_IMPORTER_GNJ = textwrap.dedent("""\
program "importer"
vars {}
procs {
    Notifica(msg: Text) from "Lib.notif" {
        codes REINICIAR<99>
    }
    from "external" import
        Avisa
}
exec Avisa(msg="oi") as "Usa Avisa" {
    pass REINICIAR
}
""")


# ---------------------------------------------------------------------------
# Testes: compile_gnj com padrão (filesystem)
# ---------------------------------------------------------------------------

class TestCompileGnjDefault:
    def test_compila_programa_minimo(self, tmp_path):
        """compile_gnj com base_dir retorna template Jinja2 válido."""
        result = compile_gnj(_MINIMAL_GNJ, base_dir=tmp_path)
        assert '{* from "genjin" import' in result
        assert "Ping" in result

    def test_retorna_string(self, tmp_path):
        result = compile_gnj(_MINIMAL_GNJ, base_dir=tmp_path)
        assert isinstance(result, str)

    def test_config_none_usa_padrao(self, tmp_path):
        """Sem config, compile_gnj usa CompilerConfig padrão."""
        result = compile_gnj(_MINIMAL_GNJ, base_dir=tmp_path, config=None)
        assert '{* from "genjin" import' in result

    def test_config_padrao_preserva_template_name(self, tmp_path):
        config = CompilerConfig()
        result = compile_gnj(_MINIMAL_GNJ, base_dir=tmp_path, config=config)
        assert '{* from "genjin" import' in result

    def test_compiler_template_name_customizado(self, tmp_path):
        config = CompilerConfig(compiler_template_name="meu_genjin")
        result = compile_gnj(_MINIMAL_GNJ, base_dir=tmp_path, config=config)
        assert '{* from "meu_genjin" import' in result
        assert '"genjin"' not in result


# ---------------------------------------------------------------------------
# Testes: GnjSourceResolver customizado (in-memory)
# ---------------------------------------------------------------------------

class TestCustomGnjResolver:
    """Testes com resolver in-memory substituindo o filesystem."""

    class InMemoryResolver:
        """Resolver que serve arquivos .gnj de um dicionário em memória."""
        def __init__(self, files: dict[str, str]):
            self._files = files

        def get_source(self, dotted_path: str) -> str:
            if dotted_path not in self._files:
                raise FileNotFoundError(f"gnj não encontrado: {dotted_path!r}")
            return self._files[dotted_path]

    def test_compile_com_resolver_customizado(self):
        resolver = self.InMemoryResolver({"external": _EXTERNAL_GNJ})
        config = CompilerConfig(gnj_resolver=resolver)
        result = compile_gnj(_IMPORTER_GNJ, config=config)
        assert "Avisa" in result

    def test_resolver_customizado_nao_precisa_de_base_dir(self):
        """Com gnj_resolver, base_dir é ignorado — não precisa de disco."""
        resolver = self.InMemoryResolver({"external": _EXTERNAL_GNJ})
        config = CompilerConfig(gnj_resolver=resolver)
        # Passa base_dir inválido — com resolver customizado deve ser ignorado
        result = compile_gnj(_IMPORTER_GNJ, base_dir=Path("/caminho/inexistente"), config=config)
        assert "Avisa" in result

    def test_resolver_customizado_nao_encontrado_levanta_erro(self):
        resolver = self.InMemoryResolver({})  # vazio
        config = CompilerConfig(gnj_resolver=resolver)
        with pytest.raises(ResolveImportError, match="external"):
            compile_gnj(_IMPORTER_GNJ, config=config)

    def test_resolve_imports_com_gnj_resolver_direto(self):
        """Testa resolve_imports() com gnj_resolver injretado diretamente."""
        resolver = self.InMemoryResolver({"external": _EXTERNAL_GNJ})
        ast = parse(_IMPORTER_GNJ)
        resolved = resolve_imports(ast, gnj_resolver=resolver)
        names = {p.name for p in resolved.procedures}
        assert "Avisa" in names

    def test_protocolo_compativel(self):
        """Verifica que InMemoryResolver satisfaz o protocolo GnjSourceResolver."""
        resolver = self.InMemoryResolver({})
        assert isinstance(resolver, GnjSourceResolver)


# ---------------------------------------------------------------------------
# Testes: FilesystemGnjResolver
# ---------------------------------------------------------------------------

class TestFilesystemGnjResolver:
    def test_resolve_arquivo_existente(self, tmp_path):
        (tmp_path / "utils.gnj").write_text(_EXTERNAL_GNJ, encoding="utf-8")
        resolver = FilesystemGnjResolver(base_dir=tmp_path)
        source = resolver.get_source("utils")
        assert 'program "external"' in source

    def test_arquivo_nao_encontrado_levanta_erro(self, tmp_path):
        resolver = FilesystemGnjResolver(base_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            resolver.get_source("nao_existe")

    def test_dotted_path_aninhado(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "util.gnj").write_text(_EXTERNAL_GNJ, encoding="utf-8")
        resolver = FilesystemGnjResolver(base_dir=tmp_path)
        source = resolver.get_source("sub.util")
        assert "external" in source

    def test_satisfaz_protocolo(self, tmp_path):
        resolver = FilesystemGnjResolver(base_dir=tmp_path)
        assert isinstance(resolver, GnjSourceResolver)


# ---------------------------------------------------------------------------
# Testes: assembler.render() com loader customizado
# ---------------------------------------------------------------------------

class TestAssemblerRender:
    """Smoke tests para assembler.render() com loader injetável."""

    _SIMPLE_TEMPLATE = "{{ nome }} funciona"

    def test_render_template_simples(self):
        result = render(self._SIMPLE_TEMPLATE, context={"nome": "genjin"})
        assert result == "genjin funciona"

    def test_render_com_dict_loader(self):
        """Loader customizado (DictLoader) resolve imports do template."""
        template_str = "{* from 'parcial' import saudacao *}{{ saudacao() }}"
        loader = DictLoader({"parcial": "{* macro saudacao() *}olá{* endmacro *}"})
        result = render(template_str, loader=loader)
        assert result == "olá"

    def test_render_sem_loader_usa_cwd(self):
        """render() sem loader não deve lançar exceção para templates sem imports."""
        result = render("{{ 1 + 1 }}")
        assert result == "2"

    def test_render_com_delimitadores_customizados(self):
        template_str = "{% if True %}ok{% endif %}"
        delimiters = {
            "block_start": "{%",
            "block_end": "%}",
            "variable_start": "{{",
            "variable_end": "}}",
            "comment_start": "{#",
            "comment_end": "#}",
        }
        result = render(template_str, delimiters=delimiters)
        assert result == "ok"


# ---------------------------------------------------------------------------
# Testes: CompilerConfig — valores padrão e campos
# ---------------------------------------------------------------------------

class TestCompilerConfig:
    def test_campos_padrao(self):
        config = CompilerConfig()
        assert config.gnj_resolver is None
        assert config.template_loader is None
        assert config.compiler_template_name == "genjin"

    def test_campos_customizaveis(self):
        class R:
            def get_source(self, dotted_path: str) -> str:
                return ""

        loader = DictLoader({})
        config = CompilerConfig(
            gnj_resolver=R(),
            template_loader=loader,
            compiler_template_name="meu_template",
        )
        assert config.gnj_resolver is not None
        assert config.template_loader is loader
        assert config.compiler_template_name == "meu_template"
