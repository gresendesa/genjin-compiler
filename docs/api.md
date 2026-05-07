# API Pública — Compilador Genjin como Biblioteca

Este documento cobre o uso do compilador Genjin como pacote Python instalável (`genjin-compiler`) com pontos de extensão customizáveis.

## Instalação

```bash
pip install genjin-compiler
# ou, em modo editable a partir do repositório:
pip install -e /caminho/para/genjin-compiler
```

---

## Uso básico

```python
from compiler import compile_gnj

# Compila um .gnj e retorna o template Jinja2 gerado
jinja2_template = compile_gnj(open("programa.gnj").read())
```

`compile_gnj` executa o pipeline completo: `Scanner → Parser → ResolveImports → Desugar → Transpiler`.

---

## `compile_gnj` — referência

```python
from compiler import compile_gnj

def compile_gnj(
    source: str,
    base_dir: Path | str | None = None,
    config: CompilerConfig | None = None,
) -> str:
```

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `source` | `str` | — | Código-fonte `.gnj` como string |
| `base_dir` | `Path \| str \| None` | `Path.cwd()` | Diretório base para resolução de imports via filesystem. Ignorado quando `config.gnj_resolver` é fornecido |
| `config` | `CompilerConfig \| None` | `CompilerConfig()` | Configuração com resolvedores. `None` usa padrões filesystem |

**Retorno:** string com o template Jinja2 gerado.

**Erros levantados:** `ScannerError`, `ParseError`, `ResolveImportError`, `DesugarError`.

---

## `CompilerConfig` — pontos de extensão

```python
from compiler import CompilerConfig
from dataclasses import dataclass

@dataclass
class CompilerConfig:
    gnj_resolver: GnjSourceResolver | None = None
    template_loader: BaseLoader | None = None
    compiler_template_name: str = "genjin"
```

### Campos

| Campo | Tipo | Padrão | Descrição |
|---|---|---|---|
| `gnj_resolver` | `GnjSourceResolver \| None` | `None` → `FilesystemGnjResolver` | Resolvedor de source `.gnj` para `from X import Y`. Substitui leitura de arquivo. |
| `template_loader` | `jinja2.BaseLoader \| None` | `None` → `DottedLoader(cwd)` | Jinja2 loader injetado no assembler. Resolve `genjin.jinja2` e outros templates. |
| `compiler_template_name` | `str` | `"genjin"` | Nome do template base emitido pelo transpiler em `{* from "X" import ... *}`. Alterar apenas se o loader usa nome diferente de `"genjin"`. |

---

## `GnjSourceResolver` — Protocol

Interface que o resolvedor de imports `.gnj` deve implementar:

```python
from compiler import GnjSourceResolver

class MeuResolver:
    def get_source(self, dotted_path: str) -> str:
        """
        Retorna o source do arquivo .gnj identificado por dotted_path.
        dotted_path: 'a.b.c' (sem extensão .gnj).
        Levantar FileNotFoundError se não encontrado.
        """
        ...
```

`dotted_path` corresponde ao caminho no `from "a.b.c" import X` do `.gnj`.

### Implementação padrão: `FilesystemGnjResolver`

```python
from compiler import FilesystemGnjResolver

resolver = FilesystemGnjResolver(base_dir="/caminho/para/raiz")
```

Converte `"a.b.c"` → `base_dir/a/b/c.gnj` e retorna o conteúdo.

---

## Uso com banco de dados (exemplo completo)

```python
from compiler import compile_gnj, CompilerConfig
from jinja2 import DictLoader
from assembler import render


class DbGnjResolver:
    """Serve arquivos .gnj diretamente do banco de dados."""

    def get_source(self, dotted_path: str) -> str:
        source = db.query("SELECT source FROM gnj_files WHERE path = ?", dotted_path)
        if source is None:
            raise FileNotFoundError(f"gnj não encontrado: {dotted_path!r}")
        return source


def compilar_e_renderizar(gnj_source: str, contexto: dict) -> str:
    # 1. Carregar templates do banco
    genjin_template = db.query("SELECT content FROM templates WHERE name = 'genjin'")
    loader = DictLoader({"genjin": genjin_template})

    # 2. Configurar o compilador
    config = CompilerConfig(
        gnj_resolver=DbGnjResolver(),    # imports .gnj do banco
        template_loader=loader,          # genjin.jinja2 do banco
    )

    # 3. Compilar .gnj → Jinja2
    jinja2_str = compile_gnj(gnj_source, config=config)

    # 4. Renderizar Jinja2 → output final
    return render(jinja2_str, loader=loader, context=contexto)
```

---

## Uso com resolvedores independentes

Cada resolvedor é substituível de forma independente. Exemplos:

```python
# Só o resolver de .gnj customizado (templates do assembler continuam no filesystem)
config = CompilerConfig(gnj_resolver=MeuDbResolver())

# Só o loader do assembler customizado (imports .gnj continuam no filesystem)
config = CompilerConfig(template_loader=DictLoader({"genjin": conteudo}))

# Nome do template base diferente (ex: template chamado "genjin_v2" no loader)
config = CompilerConfig(
    template_loader=DictLoader({"genjin_v2": conteudo}),
    compiler_template_name="genjin_v2",
)
```

---

## Entry points (CLI instalada)

Após `pip install genjin-compiler`, os seguintes comandos ficam disponíveis:

```bash
# Compilar .gnj → template Jinja2
genjin-compile programa.gnj -o saida.jinja2

# Renderizar template Jinja2
genjin-assemble saida.jinja2 -d ./code -o output.js \
  --block-start '{*' --block-end '*}'

# Pipeline completo (pipe)
genjin-compile programa.gnj | genjin-assemble - -d ./code -o output.js \
  --block-start '{*' --block-end '*}'
```

Para a referência da CLI do assembler, ver [assembler.md](assembler.md).
