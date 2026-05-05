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

> **Nota:** o tipo `Object` existe na linguagem mas **não é permitido em `vars`** — apenas em parâmetros de procedimentos. Veja a seção de `procs`.

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

#### Parâmetro por referência (singular)

```gnj
enviar(texto: Text, resposta: &Text) from "Sys.send" { ... }
```

O `&` antes do tipo indica que o argumento deve ser passado por referência a uma variável. Corresponde a `EVALUATION.REFERENCE`. Só aceita uma variável como argumento — nunca um literal.

#### Parâmetro plural (sempre por referência)

```gnj
procurar(resultados: Text[]) from "Lib.busca" { ... }
```

Parâmetros do tipo `Tipo[]` são **sempre** passados por referência. O `&` é **proibido** — a referência é implícita. Corresponde a `CARDINALITY.PLURAL` + `EVALUATION.REFERENCE` no motor.

#### Parâmetro do tipo `Object`

```gnj
executar(itens: Object) from "Lib.acao" { ... }
```

O tipo `Object` representa um valor opaco (ex: lista Python, dicionário) passado como literal de template. Não suporta `&` nem `[]`. Corresponde a `TYPE.OBJECT` no motor.

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

### Importação de proc-blocos externos (`from ... import`)

Além de declarar proc-blocos localmente, é possível importá-los de outros arquivos `.gnj`. Isso permite reutilizar lógica entre programas distintos.

```gnj
procs {
    // Procs normais declarados localmente...

    from "caminho.dotted.modulo" import
        NomeBloco1,
        NomeBloco2
}
```

A instrução `from ... import` pode aparecer em **qualquer posição dentro de `procs {}`**, intercalada com declarações locais.

#### Sintaxe

```
from "caminho.dotted" import Nome1 [, Nome2 [, ...]] [,]
```

- O caminho é uma **string com segmentos separados por pontos**.
- Os nomes são identificadores de proc-blocos ou procs normais definidos no arquivo externo.
- A vírgula final é opcional.
- **Proc-blocos** (com corpo `{ ... }`) e **procs normais** (com `from "..."`) são ambos importáveis.

#### Injeção automática de dependências

Ao importar um proc-bloco, o compilador analisa o corpo deste e injeta automaticamente todos os procs dos quais ele depende — sejam procs normais (`ProcDeclNode`) ou outros proc-blocos (`ProcBlockNode`) — incluindo dependências transitivas.

A injeção é silenciosa: se a dep já está declarada localmente com a mesma definição, ela é ignorada. Se a definição diverge, um erro de conflito é levantado.

Exemplo:

```gnj
// lenhador.gnj contém:
//   Teleportar(home: &Text) from "Federal..."  — proc normal
//   Troca_Ferramenta(...)  { ... Teleportar ... }  — proc-bloco

from "lenhador" import
    Troca_Ferramenta   // Teleportar é injetado automaticamente
```

Esse mecanismo evita declarações manuais repetidas de procs já referenciados por proc-blocos importados.

#### Resolução de path

O caminho dotted `"a.b.c"` é convertido para `a/b/c.gnj` e resolvido **em relação ao diretório do arquivo `.gnj` que está sendo compilado**.

Exemplo: se o arquivo compilado é `/projetos/lenhador/main.gnj` e contém:

```gnj
from "Federal.common.utils" import Avisa, TrocaFerramenta
```

O compilador procura o arquivo em:

```
/projetos/lenhador/Federal/common/utils.gnj
```

#### Diretório base alternativo

Para usar uma raiz diferente do diretório do arquivo fonte, passe `--import-base` na CLI:

```bash
python compiler.py main.gnj --import-base /projetos/biblioteca
```

Nesse caso, `"Federal.common.utils"` seria resolvido como `/projetos/biblioteca/Federal/common/utils.gnj`.

Quando a entrada vem de **stdin** (sem arquivo de origem), o diretório de trabalho atual (`cwd`) é usado como base padrão.

#### Regras e erros

| Situação | Comportamento |
|---|---|
| Arquivo externo não encontrado | Erro: `ResolveImportError` com o path tentado |
| Nome solicitado não existe no externo | Erro: `ResolveImportError` com o nome e o arquivo |
| Nome conflita com proc já declarado localmente (definição diferente) | Erro: `ResolveImportError` com o nome em conflito |
| Dep injetada automaticamente conflita com definição local | Erro: `ResolveImportError` de conflito de definição |
| Importação circular (A importa B que importa A) | Erro: `ResolveImportError` indicando o ciclo |
| Arquivo externo também usa `from ... import` | Resolvido recursivamente (importação em cadeia) |

#### Exemplo

Arquivo `Federal/common/lenhador_utils.gnj`:
```gnj
program "lenhador-utils"

vars {}

procs {
    NotificaErro(mensagem: Text) from "Federal.@.Lenhador.notificar_exceção" {
        codes REINICIAR_CICLO<99>
    }

    Exceção_e_Reinicia(mensagem: Text) {
        exec NotificaErro(mensagem=mensagem) as "Notifica e reinicia" {
            pass REINICIAR_CICLO
        }
    }
}

exec NotificaErro(mensagem="boot") as "Boot" {
    pass REINICIAR_CICLO
}
```

Arquivo `main.gnj`:
```gnj
procs {
    NotificaErro(mensagem: Text) from "Federal.@.Lenhador.notificar_exceção" {
        codes REINICIAR_CICLO<99>
    }

    from "Federal.common.lenhador_utils" import
        Exceção_e_Reinicia
}
```

O proc-bloco `Exceção_e_Reinicia` fica disponível em `main.gnj` exatamente como se fosse declarado localmente.

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
| `while(CODIGO)` ou `while(A, B, ...)` | Repetição condicional | `ATTRIBUTE.LOOP_WHILE` |
| `pass CODIGO, ...` | Delegação de códigos | `ATTRIBUTE.PASS_CODES` |

---

## Notação inline (`@proc()`)

A notação inline é um **açúcar sintático** que permite expressar um bloco `exec` simples de forma compacta, sem chaves e sem `case` explícito. É expandida pelo compilador na fase **desugar** antes da transpilação.

### Gramática

```
inline_seq  ::= inline_atom+ terminal
inline_atom ::= '@' IDENT '(' [arg_list] ')' ['>>' IDENT] ['while' '(' IDENT {',' IDENT}* ')'] 'when' '(' IDENT ')'
terminal    ::= '@' IDENT '(' [arg_list] ')' ['>>' IDENT] ['while' '(' IDENT {',' IDENT}* ')']
             |  exec_block
```

**Regra de ordem:** dentro de cada átomo, os modificadores devem aparecer na seguinte sequência fixa:

```
@proc([args]) [>> var] [while(CODE)] [when(CODE)]
```

### Tipo 1 — átomo simples (sem `when`)

Um único átomo sem `when` é expandido para um `exec` canônico sem cases:

```gnj
@proc() >> var
@proc() >> var while(ERR)
@proc() >> var while(ERR, TIMEOUT)
```

Equivalências:

| Notação inline | Equivalente canônico |
|---|---|
| `@proc() >> var` | `exec proc() >> var { pass <todos os códigos> }` |
| `@proc() >> var while(ERR)` | `exec proc() >> var { pass <todos exceto ERR> } while(ERR)` |
| `@proc() >> var while(ERR, TIMEOUT)` | `exec proc() >> var { pass <todos exceto ERR e TIMEOUT> } while(ERR, TIMEOUT)` |

### Tipo 2 — encadeamento com `when`

Dois ou mais átomos, onde todos exceto o último possuem `when(CODE)`:

```gnj
@proc() when(OK)
@proc() >> var
```

O átomo com `when(CODE)` vira o bloco externo. O code indicado em `when` é colocado como `case` para o próximo átomo, e o `pass` do externo recebe os demais códigos.

**Exemplo: dois átomos**

```gnj
@autenticar() when(OK)
@carregar_dados() >> res
```

Expande para:

```gnj
exec autenticar() {
    case OK: exec carregar_dados() >> res {
        pass <todos os códigos de carregar_dados>
    }
    pass ERR   /* demais códigos de autenticar */
}
```

**Exemplo: três átomos**

```gnj
@verificar_rede() when(ONLINE)
@autenticar()     when(OK)
@carregar_dados() >> res
```

Expande para:

```gnj
exec verificar_rede() {
    case ONLINE: exec autenticar() {
        case OK: exec carregar_dados() >> res {
            pass <todos os códigos de carregar_dados>
        }
        pass ERR
    }
    pass OFFLINE
}
```

### Uso em `case` body

A notação inline também pode ser usada como corpo de um `case` dentro de um `exec` canônico:

```gnj
exec verificar_rede() >> s {
    case ONLINE: @autenticar() when(OK)
                 @carregar_dados() >> res
    pass OFFLINE
}
```

### Restrições

- `when` só é permitido em átomos não-terminais (todos exceto o último).
- O átomo terminal não pode ter `when`.
- A ordem dos modificadores é obrigatória: `[>>] [while] [when]`.
- O `CODE` em `when(CODE)` deve ser um código de saída válido do proc daquele átomo.
- O `while` aceita **um ou mais códigos** separados por vírgula: `while(A)`, `while(A, B)`, etc.
- Os códigos em `while` **não** precisam ser declarados no proc — códigos borbulhados de procs filhos são permitidos.

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
