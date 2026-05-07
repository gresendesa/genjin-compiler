# assembler.py

Renderiza templates Jinja2 a partir da linha de comando ou via API Python, com suporte a diretório de templates, variáveis de contexto, delimitadores customizados e loader Jinja2 injetável.

## Uso — CLI

```
python assembler.py <template> -d <dir> -o <saída> [opções]
```

## Argumentos

| Argumento | Obrigatório | Descrição |
|---|:---:|---|
| `template` | ✓ | Arquivo de template de entrada (ponto de entrada) |
| `-d, --templates-dir` | | Diretório raiz dos templates para `extends`/`include`/`import`. Padrão: diretório do template |
| `-o, --output` | ✓ | Arquivo de saída |
| `-v CHAVE=VALOR` | | Variável de contexto inline (repetível) |
| `-f, --vars-file` | | Arquivo JSON com variáveis de contexto. Mesclado com `-v`, que tem precedência |

### Delimitadores customizados

| Argumento | Padrão | Deste projeto |
|---|---|---|
| `--block-start` / `--block-end` | `{%` / `%}` | `{*` / `*}` |
| `--variable-start` / `--variable-end` | `{{` / `}}` | — |
| `--comment-start` / `--comment-end` | `{#` / `#}` | — |

## Exemplos — CLI

```bash
# Template deste projeto (delimitadores {* *})
python assembler.py implementation.jinja2 -d . -o output.js \
  --block-start '{*' --block-end '*}'

# Variáveis inline
python assembler.py main.j2 -d ./tpl -o result.txt -v nome=Mundo -v versao=2

# Variáveis via JSON
python assembler.py main.j2 -d ./tpl -o result.txt -f vars.json

# JSON + inline (inline tem precedência)
python assembler.py main.j2 -d ./tpl -o result.txt -f vars.json -v versao=3
```

## vars.json — formato esperado

Objeto JSON plano ou aninhado no nível raiz:

```json
{
  "nome": "Mundo",
  "versao": 2,
  "config": { "debug": true }
}
```

---

## Uso — API Python (`render`)

Além da CLI, o assembler expõe a função `render()` para uso programático como biblioteca. Isso permite renderizar templates sem passar pelo sistema de arquivos, injetando um Jinja2 `BaseLoader` customizado.

```python
from assembler import render
```

### Assinatura

```python
def render(
    template_str: str,
    loader=None,
    context: dict | None = None,
    delimiters: dict | None = None,
) -> str:
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `template_str` | `str` | — | Conteúdo do template a renderizar |
| `loader` | `jinja2.BaseLoader` | `DottedLoader(cwd)` | Loader para resolver templates referenciados (ex: `genjin.jinja2`) |
| `context` | `dict` | `{}` | Variáveis passadas ao template |
| `delimiters` | `dict` | delimitadores do projeto | Chaves opcionais: `block_start`, `block_end`, `variable_start`, `variable_end`, `comment_start`, `comment_end` |

### Retorno

String com o conteúdo renderizado. Levanta `TemplateSyntaxError`, `TemplateNotFound` ou `Exception` em caso de erro.

### Exemplos

```python
from assembler import render
from jinja2 import DictLoader

# Renderização simples
resultado = render("{{ nome }} funciona", context={"nome": "genjin"})

# Com loader customizado (templates em memória — sem disco)
loader = DictLoader({
    "genjin": conteudo_genjin_jinja2,
    "meu_template": conteudo_outro_template,
})
resultado = render(saida_do_compilador, loader=loader)

# Com delimitadores customizados
resultado = render(
    "{% if True %}ok{% endif %}",
    delimiters={"block_start": "{%", "block_end": "%}",
                "comment_start": "{#", "comment_end": "#}"},
)
```

### Pipeline completo sem disco

```python
from compiler import compile_gnj, CompilerConfig
from jinja2 import DictLoader
from assembler import render

# Resolvedores em memória (ex: banco de dados)
loader = DictLoader({"genjin": db.get("genjin_template")})
config = CompilerConfig(
    gnj_resolver=MeuDbResolver(),
    template_loader=loader,
)

jinja2_str = compile_gnj(gnj_source, config=config)
output = render(jinja2_str, loader=loader)
```

> Para a documentação completa da API de extensão do compilador (resolvedores customizáveis), ver [api.md](api.md).
