# GenJin Compiler

> **GenJin** (Gerador Jinja) é um transpilador de macros baseado em Jinja2. Ele processa templates com delimitadores customizados e valida a árvore de decisões do programa em tempo de compilação, garantindo que nenhuma condição de saída fique sem tratamento.

## Visão geral

O GenJin usa o Jinja2 como motor de templates e expõe uma CLI (`compiler.py`) que recebe um arquivo de entrada e um diretório de templates. A saída é escrita no **stdout**, permitindo redirecionamento e encadeamento com outros scripts. Os delimitadores padrão do projeto diferem dos padrões do Jinja2:

| Função       | Padrão Jinja2 | GenJin      |
|---|---|---|
| Bloco        | `{% ... %}`   | `{* ... *}` |
| Variável     | `{{ ... }}`   | `{{ ... }}` |
| Comentário   | `{# ... #}`   | `{!! ... !!}` |

## Estrutura do repositório

```
compiler.py              # Ponto de entrada da CLI
assembler.py             # Lógica central de renderização
requirements.txt
tests/
  conftest.py            # Fixture compartilhada (make_env)
  delimiters/
    templates/           # Templates de entrada dos testes
    expected/            # Saídas esperadas (golden files)
    test_delimiters.py   # Suite de testes de delimitadores
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python compiler.py <template> -d <dir-de-templates> [opções]
```

A saída é escrita no **stdout**. Use redirecionamento para salvar ou encadear com outros scripts:

```bash
# Salvar em arquivo
python compiler.py code/genjin.jinja2 -d code \
  --block-start '{*'  --block-end '*}'       \
  --variable-start '{{' --variable-end '}}'  \
  --comment-start '{!!' --comment-end '!!}' > output.js

# Encadear com outro script
python compiler.py code/genjin.jinja2 -d code ... | python outro_script.py
```

### Opções disponíveis

| Opção | Descrição |
|---|---|
| `-d, --templates-dir` | Diretório raiz dos templates para `extends`/`include`/`import` |
| `-v CHAVE=VALOR` | Variável de contexto inline (repetível) |
| `-f, --vars-file` | Arquivo JSON com variáveis de contexto |
| `--block-start/end` | Delimitadores de bloco |
| `--variable-start/end` | Delimitadores de variável |
| `--comment-start/end` | Delimitadores de comentário |

## Testes

Os testes usam **pytest** e cobrem os três tipos de delimitadores e composição de templates (`include`/`extends`).

```bash
# Todos os testes
.venv/bin/pytest tests/ -v

# Apenas delimitadores
.venv/bin/pytest tests/delimiters/ -v
```

Cada teste renderiza um template em `tests/delimiters/templates/` e compara o resultado byte a byte com o arquivo correspondente em `tests/delimiters/expected/`.

## Testes com templates de código Mod Macro

```bash
python assembler.py code/tests/basic.jinja2 -d code/ | python mkb/indenter.py
```
