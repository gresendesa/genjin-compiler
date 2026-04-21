# assembler.py

Renderiza templates Jinja2 a partir da linha de comando, com suporte a diretório de templates, variáveis de contexto e delimitadores customizados.

## Uso

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

## Exemplos

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
