# GenJin Compiler

> **GenJin** (Gerador Jinja) é um transpilador de macros baseado em Jinja2. Ele processa templates com delimitadores customizados e valida a árvore de decisões do programa em tempo de compilação, garantindo que nenhuma condição de saída fique sem tratamento.

## Visão geral

O GenJin usa o Jinja2 como motor de templates e expõe uma CLI (`compiler.py`) que recebe um arquivo de entrada, um diretório de templates e um arquivo de saída. Os delimitadores padrão do projeto diferem dos padrões do Jinja2:

| Função       | Padrão Jinja2 | GenJin      |
|---|---|---|
| Bloco        | `{% ... %}`   | `{* ... *}` |
| Variável     | `{{ ... }}`   | `{{ ... }}` |
| Comentário   | `{# ... #}`   | `{!! ... !!}` |

## Estrutura do repositório

```
compiler.py              # Ponto de entrada da CLI
assembler.py             # Lógica central de renderização
implementation.jinja2    # Template principal do projeto
example.sh               # Exemplo de uso completo
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
python compiler.py <template> -d <dir-de-templates> -o <saída> [opções]
```

### Exemplo completo

```bash
python compiler.py examples/implementation.jinja2 -d . -o output/output.js
```

### Opções disponíveis

| Opção | Descrição |
|---|---|
| `-d, --templates-dir` | Diretório raiz dos templates para `extends`/`include`/`import` |
| `-o, --output` | Arquivo de saída **(obrigatório)** |
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
