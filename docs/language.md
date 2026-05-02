# Linguagem Genjin — Referência da Sintaxe `.gnj`

Versão: 1.0.0
Status: ativo
Data: 2026-04-27

---

## Sobre este documento

Este documento descreve a sintaxe completa da linguagem `.gnj` — a DSL de alto nível do projeto Genjin.

Um arquivo `.gnj` é compilado pelo compilador (`compiler/`) e produz um template Jinja2 que é executado pelo assembler (`assembler.py`) usando o motor Genjin (`code/genjin.jinja2`).

**Referências obrigatórias para entender a semântica:**
- `docs/genjin.md` — especificação semântica completa (célula de operação, cadeia de responsabilidade, etc.)
- `code/genjin.jinja2` — implementação do motor (atributos, tipos, cardinalidades, avaliações)

---

## Estrutura geral de um programa

Todo programa `.gnj` é composto por três seções obrigatórias. A única restrição posicional é que `program` deve ser a **primeira** palavra-chave do arquivo. Os blocos `vars`, `procs` e `exec` podem aparecer em **qualquer ordem**:

```gnj
program "nome do programa"

vars {
    /* declarações de variáveis */
}

procs {
    /* declarações de procedimentos */
}

exec nome_do_proc(...) >> variavel_raiz {
    /* fluxo de execução */
}
```

| Seção | Obrigatória | Descrição |
|---|:---:|---|
| `program` | sim | Declara o nome do programa. **Deve ser a primeira linha.** |
| `vars` | sim | Declara as variáveis de estado. Pode vir em qualquer ordem após `program`. |
| `procs` | sim | Declara os procedimentos disponíveis. Pode vir em qualquer ordem após `program`. |
| `exec` (raiz) | sim | Define o fluxo de execução. Exatamente um bloco raiz por programa. Pode vir em qualquer ordem após `program`. |

---

## Comentários

A linguagem suporta dois estilos de comentário:

```gnj
// Comentário de linha — ignorado até o fim da linha

/* Comentário de bloco
   pode ocupar múltiplas linhas */
```

---

## Declaração do programa

```gnj
program "nome do programa"
```

- O nome é uma string literal entre aspas duplas.
- Corresponde a `ATTRIBUTE.NAME` no motor Genjin.

**Exemplo:**
```gnj
program "Sistema de Pagamento"
```

---

## Bloco de variáveis (`vars`)

Declara todas as variáveis de estado do programa.

```gnj
vars {
    nome: Tipo
    nome: Tipo = valor_inicial
    nome: Tipo[]
}
```

### Tipos primitivos

| Tipo `.gnj` | Equivalente no motor | Descrição |
|---|---|---|
| `Number` | `TYPE.NUMBER` | Número inteiro ou decimal |
| `Text` | `TYPE.TEXT` | Cadeia de texto |
| `Logic` | `TYPE.LOGIC` | Booleano (`true` / `false`) |

### Cardinalidade

| Sintaxe | Equivalente no motor | Descrição |
|---|---|---|
| `nome: Tipo` | `CARDINALITY.SINGULAR` | Valor único |
| `nome: Tipo[]` | `CARDINALITY.PLURAL` | Lista de valores |

### Valor inicial

Uma variável pode ter um valor inicial declarado com `=`:

```gnj
status_conexao: Text = "idle"
```

Corresponde a `ATTRIBUTE.VALUE` no motor. Variáveis sem valor inicial não possuem `ATTRIBUTE.VALUE`.

### Exemplos

```gnj
vars {
    status_var: Number          // singular, sem valor inicial
    status_var2: Number         // singular, sem valor inicial
    status_conexao: Text = "idle"  // singular, com valor inicial
    res: Text                   // singular, sem valor inicial
    minha_lista: Text[]         // plural (lista)
}
```

---

## Bloco de procedimentos (`procs`)

Declara todos os procedimentos disponíveis para uso nos blocos `exec`.

```gnj
procs {
    nome(parametros) from "caminho.macro" {
        codes NOME<codigo>, ...
    }
}
```

> **Nota:** a keyword `proc` foi removida. Dentro de `procs { }`, os procedimentos são declarados diretamente pelo nome, sem prefixo.

### Resolução do `from`

O caminho em `from` é uma string que segue a regra: **o último segmento (após o último ponto) é o nome da macro; o restante é o caminho da biblioteca.**

| `from` na sintaxe | Equivalente Jinja2 | `ATTRIBUTE.MACRO` no motor |
|---|---|---|
| `"Net.check"` | `{* from "Net" import check *}` | `('Net', 'check')` |
| `"Sys.sleep"` | `{* from "Sys" import sleep *}` | `('Sys', 'sleep')` |
| `"Federal.@.GenJin"` | `{* from "Federal.@" import GenJin *}` | `('Federal.@', 'GenJin')` |

### Parâmetros

Um procedimento pode ter zero ou mais parâmetros. Cada parâmetro tem nome e tipo.

#### Parâmetro por valor (literal)

```gnj
esperar(segundos: Number) from "Sys.sleep" { ... }
```

O argumento será passado como um valor literal. Corresponde a `EVALUATION.LITERAL`.

#### Parâmetro por referência

```gnj
enviar(texto: Text, resposta: &Text) from "Sys.send" { ... }
```

O `&` antes do tipo indica que o argumento deve ser passado por referência a uma variável. Corresponde a `EVALUATION.REFERENCE`. Só aceita uma variável como argumento — nunca um literal.

### Códigos de saída (`codes`)

Todo procedimento declara os códigos que pode retornar:

```gnj
codes NOME<numero>, NOME<numero>, ...
```

| Parte | Equivalente no motor | Descrição |
|---|---|---|
| `NOME` | `ATTRIBUTE.NAME` do output code | Identificador simbólico do código |
| `<numero>` | `ATTRIBUTE.CODE` | Valor numérico do código |

**Exemplo:**
```gnj
verificar_rede() from "Net.check" {
    codes ONLINE<0>, OFFLINE<1>
}
```

### Exemplos completos de `procs`

```gnj
procs {
    verificar_rede() from "Net.check" {
        codes ONLINE<0>, OFFLINE<1>
    }

    esperar(segundos: Number) from "Sys.sleep" {
        codes DONE<0>, ERROR<5>
    }

    enviar(texto: Text, resposta: &Text) from "Sys.send" {
        codes OK<0>, TIMEOUT<10>
    }
}
```

---

## Bloco de execução (`exec`)

O `exec` é a unidade fundamental de execução. Define qual procedimento executar, qual variável recebe o código de saída e como tratar cada resultado.

```gnj
exec nome_do_proc(argumentos) >> variavel {
    case CODIGO : exec ...
    ...
    pass CODIGO, CODIGO, ...
}
```

### Vinculação de variável (`>>`)

O operador `>>` associa o bloco a uma variável de estado. Após a execução do procedimento, o código de saída é armazenado nessa variável.

```gnj
exec verificar_rede() >> status_var { ... }
```

Corresponde a `ATTRIBUTE.VARIABLE` no motor.

### Herança de variável

Se um `exec` não declara `>>`, ele herda a variável do bloco `exec` pai imediato.

```gnj
exec verificar_rede() >> status_var {
    case OFFLINE : exec esperar(segundos=5) {
        // Este exec herda status_var do pai
        pass DONE, ERROR
    }
}
```

### Nome do bloco (`as`)

Por padrão, o nome do bloco é o nome do procedimento invocado. Para dar um nome explícito, use `as`. O `as` deve vir **antes** de `>>`:

```gnj
exec esperar(segundos=5) as "aguardar_rede" { ... }
exec esperar(segundos=5) as "aguardar_rede" >> status_var { ... }
```

Corresponde a `ATTRIBUTE.NAME` no motor.

### Argumentos

Os argumentos são passados como pares `nome=valor`:

#### Argumento literal

```gnj
exec esperar(segundos=5) { ... }
exec enviar(texto="OK", ...) { ... }
```

O valor é passado diretamente. Corresponde a `EVALUATION.LITERAL`.

#### Argumento por referência

```gnj
exec enviar(texto="OK", resposta=&res) { ... }
```

O `&` antes do nome da variável indica passagem por referência. Corresponde a `EVALUATION.REFERENCE`. O tipo da variável deve ser compatível com o tipo do parâmetro correspondente.

---

## Tratamento de códigos no `exec`

Dentro de um bloco `exec`, cada código de saída possível do procedimento deve ser tratado de uma das três formas:

| Construto | Equivalente no motor | Quando usar |
|---|---|---|
| `case CODIGO : exec ...` | `ATTRIBUTE.CASES` | Tratar o código executando um bloco filho |
| `while(CODIGO)` | `ATTRIBUTE.LOOP_WHILE` | Repetir este bloco quando o código ocorrer |
| `pass CODIGO, ...` | `ATTRIBUTE.PASS_CODES` | Delegar o código ao bloco pai |

**Regra:** todo código que não é tratado por `case` ou `while` **deve** aparecer em `pass`. O corpo de um `exec` nunca pode estar vazio.

### `case` — ramificação

```gnj
case OFFLINE : exec esperar(segundos=5) { ... }
```

- Um `case` sempre leva a um bloco `exec` filho.
- O exec filho pode ter seu próprio `>>` para redeclarar a variável, ou herdar do pai.
- Um bloco `exec` pode ter **múltiplos `case` no mesmo nível**, um para cada código que se deseja ramificar:

```gnj
exec verificar_rede() >> status_var {
    case OFFLINE  : exec tratar_offline() { ... }
    case DEGRADED : exec tratar_degradado() { ... }
    case ERROR    : exec tratar_erro() { ... }
    pass ONLINE
}
```

Cada `case` trata um código distinto. A ordem de declaração não afeta a semântica — o motor avalia pelo valor do código.

### `while` — repetição

```gnj
exec esperar(segundos=5) {
    case DONE : exec enviar(...) { ... }
} while(ERROR)
```

- O `while(CODIGO)` aparece **após o `}` do exec imediatamente acima**.
- Quando o código especificado ocorre (incluindo os retornos de blocos filhos), o `exec` é executado novamente.
- Corresponde a `ATTRIBUTE.LOOP_WHILE`.

### `pass` — delegação

```gnj
pass ONLINE, OK, TIMEOUT
```

- Lista de códigos separados por vírgula.
- Obrigatório para todos os códigos não cobertos por `case` ou `while`.
- O bloco pai (ou o escopo raiz do programa) fica responsável por tratar esses códigos.
- Corresponde a `ATTRIBUTE.PASS_CODES`.

### Exemplo completo de exec

```gnj
exec verificar_rede() >> status_var {
    case OFFLINE : exec esperar(segundos=5) {
        case DONE : exec enviar(texto="OK", resposta=&res) >> status_var2 {
            pass OK, TIMEOUT
        }
    } while(ERROR)

    pass ONLINE, OK, TIMEOUT
}
```

**Leitura do exemplo:**
1. Executa `verificar_rede()` e armazena o resultado em `status_var`.
2. Se o resultado for `OFFLINE`: executa `esperar(segundos=5)` (herda `status_var`).
   - Se `esperar` retornar `DONE`: executa `enviar(texto="OK", resposta=&res)` armazenando em `status_var2`.
     - `OK` e `TIMEOUT` são delegados ao bloco pai.
   - Se `esperar` retornar `ERROR`: o bloco `esperar` é repetido (`while`).
3. Os códigos `ONLINE`, `OK` e `TIMEOUT` são delegados para fora.

---

## Mapeamento completo: sintaxe `.gnj` → motor Genjin

| Sintaxe `.gnj` | Conceito em `genjin.md` | Atributo em `genjin.jinja2` |
|---|---|---|
| `program "nome"` | Nome do programa | `ATTRIBUTE.NAME` |
| `vars { ... }` | Lista de variáveis | `ATTRIBUTE.VARIABLES` |
| `nome: Tipo` | Variável singular | `ATTRIBUTE.TYPE` + `CARDINALITY.SINGULAR` |
| `nome: Tipo = valor` | Variável com valor inicial | `ATTRIBUTE.VALUE` |
| `nome: Tipo[]` | Variável plural | `ATTRIBUTE.CARDINALITY` → `CARDINALITY.PLURAL` |
| `Number` | Tipo numérico | `TYPE.NUMBER` |
| `Text` | Tipo texto | `TYPE.TEXT` |
| `Logic` | Tipo lógico | `TYPE.LOGIC` |
| `procs { ... }` | Lista de procedimentos | `ATTRIBUTE.PROCEDURES` |
| `nome(...) from "a.b"` | Procedimento com macro | `ATTRIBUTE.NAME`, `ATTRIBUTE.MACRO: ('a', 'b')` |
| `param: Tipo` | Parâmetro por valor | `ATTRIBUTE.EVALUATION` → `EVALUATION.LITERAL` |
| `param: &Tipo` | Parâmetro por referência | `ATTRIBUTE.EVALUATION` → `EVALUATION.REFERENCE` |
| `codes NOME<n>` | Código de saída | `ATTRIBUTE.OUTPUT_CODES`: `{NAME, CODE}` |
| `exec proc() >> var { }` | Bloco com variável vinculada | `ATTRIBUTE.BLOCK`, `ATTRIBUTE.VARIABLE`, `ATTRIBUTE.PROCEDURE` |
| `exec proc() as "nome" { }` | Bloco com nome explícito | `ATTRIBUTE.NAME` |
| `exec` sem `>>` | Herança de variável do pai | `ATTRIBUTE.VARIABLE` ausente → herda |
| `param=valor` | Argumento literal | `EVALUATION.LITERAL` |
| `param=&var` | Argumento por referência | `EVALUATION.REFERENCE` |
| `case NOME : exec ...` | Ramificação por código | `ATTRIBUTE.CASES` + `ATTRIBUTE.OUTPUT_CODE` |
| `while(CODIGO)` | Repetição condicional | `ATTRIBUTE.LOOP_WHILE` |
| `pass CODIGO, ...` | Delegação de códigos | `ATTRIBUTE.PASS_CODES` |

---

## Exemplo completo anotado

```gnj
program "Sistema de Pagamento"        // ATTRIBUTE.NAME do programa

vars {
    status_var: Number                 // ATTRIBUTE.TYPE=NUMBER, CARDINALITY=SINGULAR
    status_var2: Number
    status_conexao: Text = "idle"      // ATTRIBUTE.VALUE = "idle"
    res: Text
    minha_lista: Text[]                // CARDINALITY=PLURAL
}

procs {
    verificar_rede() from "Net.check" {    // MACRO: ('Net', 'check')
        codes ONLINE<0>, OFFLINE<1>             // OUTPUT_CODES
    }

    esperar(segundos: Number) from "Sys.sleep" {   // param literal
        codes DONE<0>, ERROR<5>
    }

    enviar(texto: Text, resposta: &Text) from "Sys.send" {  // resposta: ref
        codes OK<0>, TIMEOUT<10>
    }
}

// Bloco raiz: vincula a status_var. Nome padrão = "verificar_rede"
exec verificar_rede() >> status_var {

    // CASES: se OFFLINE, executa esperar (herda status_var)
    case OFFLINE : exec esperar(segundos=5) {

        // CASES: se DONE, executa enviar com status_var2
        case DONE : exec enviar(texto="OK", resposta=&res) >> status_var2 {
            pass OK, TIMEOUT   // PASS_CODES de status_var2
        }

        // PASS_CODES de status_var (herdada)
        // ERROR é tratado pelo while abaixo — não vai aqui

    } while(ERROR)    // LOOP_WHILE: repete esperar se ERROR

    pass ONLINE, OK, TIMEOUT   // PASS_CODES do bloco raiz
}
```
