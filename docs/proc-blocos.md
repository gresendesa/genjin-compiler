# Proc-Blocos — Especificação Preliminar

Versão: 0.2 (proposta — aguardando implementação)
Status: rascunho ativo
Sprint de especificação: SPR-2026-10 (B-017)
Última atualização: 2026-05-03 (B-018 concluído — gap Object resolvido; B-019/B-020 criados)

---

## Sobre este documento

Este documento especifica a proposta de **proc-blocos**: um mecanismo para declarar sub-programas
reutilizáveis com parâmetros de transpilação na linguagem Genjin (`.gnj`).

Esta é uma especificação **preliminar**. A implementação deve seguir as decisões registradas em
`ia/decisions.md` (DEC-003). Qualquer mudança de contrato em relação a este documento requer
atualização de versão e registro em `ia/decisions.md`.

**Referências obrigatórias:**
- `docs/language.md` — referência completa da sintaxe `.gnj`
- `docs/genjin.md` — especificação semântica do motor (blocos, procedimentos, variáveis)
- `ia/decisions.md` — DEC-003 (decisão de sintaxe e estratégia)

---

## Motivação

Um programa Genjin real frequentemente repete o mesmo padrão de tratamento de erro em múltiplos
pontos. Exemplo do `Lenhador.jinja2`: o tratamento de "ferramenta gasta" (teleportar, guardar,
pegar nova, voltar) aparece em diferentes contextos, com pequenas variações (qual home usar, qual
gaveta de MKB). Hoje, o programador repete o bloco inteiro cada vez, ou usa dicionários Jinja2
manualmente.

Proc-blocos permitem declarar esse padrão **uma vez** em `procs { }` e reutilizá-lo com
**parâmetros de transpilação** — valores resolvidos pelo compilador na hora da expansão.

---

## Conceito: parâmetros de transpilação vs. parâmetros de runtime

| | Proc normal (`from`) | Proc-bloco |
|---|---|---|
| Resolvido em | Runtime (bot/interpretador) | Transpilação (compilador Genjin) |
| Parâmetro representa | Valor passado ao procedimento externo | Placeholder substituído no bloco |
| Sintaxe de declaração | `param: Type` / `param: &Type` | Idêntica |
| Sintaxe de chamada | `param=valor` / `param=&var` | Idêntica |
| Aparece no Jinja2 gerado | Argumento de template call | Valor embutido literalmente no bloco expandido |
| Precisa existir em `vars`? | Sim (se `&`) | Não — é nome de substituição |
| Múltiplas chamadas | Mesmo proc, valores distintos em runtime | Cópias independentes na AST gerada |

---

## Sintaxe de declaração

Um proc-bloco é declarado dentro de `procs { }`, sem a keyword `from`:

```gnj
procs {
    // Proc normal (tem from)
    Teleportar(home: &Text) from "Federal.@.server_tools.Teleportar" {
        codes SUCESSO<0>, DEMORA<1>, CANCELADO<2>
    }

    // Proc-bloco (sem from — corpo é um exec)
    NomeDoBloco(param1: &Text, param2: Text) {
        exec ProcNormal(arg=&param1) {
            pass SUCESSO, CANCELADO
        } while(DEMORA)
    }
}
```

### Regras de declaração

1. **Identificação:** ausência de `from` + corpo `{ exec ... }` → proc-bloco. Presença de `from`
   → proc normal. Nunca ambos.

2. **Parâmetros:**
   - `param: &Type` → placeholder **ref** — na expansão, substituído pelo nome de uma variável
     real do programa (passado com `=&var` na chamada)
   - `param: Type` → placeholder **lit** — na expansão, substituído pelo valor literal (passado
     com `=valor` na chamada)
   - Tipo `Object` é permitido para placeholder lit (permite passar listas/dicionários)
   - Cardinalidade plural (`param: Type[]`) não é permitida em proc-blocos

3. **Corpo:** exatamente um `exec` no nível raiz do corpo. O `exec` mais externo **não pode
   declarar `>>`** — a variável de resultado é herdada do contexto do ponto de chamada.
   `exec` internos (dentro de `case`) podem declarar `>>` normalmente.

4. **Referências internas:** o corpo pode referenciar:
   - Procs normais declarados em `procs`
   - Outros proc-blocos (desde que sem ciclos — ver seção de recursão)
   - Parâmetros do próprio proc-bloco como pseudo-variáveis

5. **Escopo de variáveis:** variáveis reais do programa (`vars`) são acessíveis normalmente
   dentro do corpo. Parâmetros `ref` funcionam como se fossem variáveis declaradas em `vars`
   durante o parse do corpo.

---

## Sintaxe de chamada

Proc-blocos são chamados com a mesma notação `@` já existente (B-015):

```gnj
@NomeDoBloco(param1=&minha_var, param2="valor_literal")
```

Ou como corpo de `case`:

```gnj
exec AlgumProc() >> resultado {
    case ERRO: @NomeDoBloco(param1=&home_machados_gastos, param2="slot_a")
    pass SUCESSO
}
```

### Regras de chamada

- O compilador resolve se o alvo do `@` é `ProcDeclNode` ou `ProcBlockNode` pelo nome
- Para proc-blocos: os argumentos são parâmetros de transpilação, não passados ao motor
- Todos os parâmetros declarados devem ter argumento correspondente na chamada (sem parâmetros opcionais)
- `>>` na chamada não é permitido (a variável já é herdada do contexto)
- `while(CODE)` na chamada não é permitido (o `while` fica dentro do corpo do proc-bloco)
- `when(CODE)` é permitido — permite encadear a saída do proc-bloco com o próximo bloco inline

---

## Códigos de saída inferidos

O compilador infere automaticamente os códigos de saída de um proc-bloco a partir dos
`pass_codes` do bloco mais externo do corpo. Não existe sintaxe `codes { }` em proc-blocos.

**Exemplo:**

```gnj
Ferramenta_Gasta(home_destino: &Text, gaveta_guardar: Text) {
    exec Teleportar(home=&home_destino) {
        case SUCESSO:
            exec Guardar_Itens(gaveta=gaveta_guardar, itens=["diamond_axe"]) {
                pass SUCESSO, DEMORA
            }
        pass CANCELADO, SUCESSO   // ← estes são os códigos inferidos do proc-bloco
    } while(DEMORA)
}
```

Códigos de saída inferidos: `CANCELADO`, `SUCESSO`.

O ponto de chamada `@Ferramenta_Gasta(...)` pode referenciar esses códigos em `when(CODE)` ou
no `pass`/`case` externo.

---

## Detecção de recursão

Proc-blocos **não podem se referenciar direta ou indiretamente**. O compilador detecta ciclos
antes de qualquer expansão.

**Exemplos proibidos:**

```gnj
// Recursão direta — ERRO
A() {
    exec B() {
        case SUCESSO: @A()   // A referencia A
        pass ERRO
    }
}

// Recursão indireta — ERRO
A() { exec B() { case OK: @B_Bloco() pass ERR } }
B_Bloco() { exec C() { case OK: @A() pass ERR } }   // ciclo: A → B_Bloco → A
```

**O compilador emite:**

```
DesugarError: recursão detectada em proc-blocos: A → B_Bloco → A
```

**Composição permitida (sem ciclo):**

```gnj
// B_Bloco usa A_Bloco — permitido, desde que A_Bloco não use B_Bloco
A_Bloco(x: &Text) { exec ProcA(v=&x) { pass SUCESSO, ERRO } }
B_Bloco(y: &Text) { exec ProcB(v=&y) { case SUCESSO: @A_Bloco(x=&y) pass ERRO } }
```

---

## Expansão pelo compilador

Ao encontrar `@Ferramenta_Gasta(home_destino=&home_machados_gastos, gaveta_guardar="slot_a")`,
o compilador (fase `desugar.py`) executa:

1. Localiza `ProcBlockNode` de `Ferramenta_Gasta`
2. Constrói mapeamento de substituição: `{home_destino → ArgNode(value='home_machados_gastos', evaluation='reference'), gaveta_guardar → ArgNode(value='slot_a', evaluation='literal')}`
3. Faz `copy.deepcopy` da AST do bloco interno
4. Aplica visitor recursivo ao clone, substituindo cada `ArgNode` cujo `value` bate com um placeholder
5. Insere o bloco clonado e substituído no ponto de chamada
6. O bloco herdará a variável de resultado do `exec` pai

Cada chamada com parâmetros diferentes gera uma **cópia autônoma** no Jinja2 gerado.

---

## Exemplo completo

```gnj
program "lenhador"

procs {
    Teleportar(home: &Text) from "Federal.@.server_tools.Teleportar" {
        codes SUCESSO<0>, DEMORA<1>, CANCELADO<2>
    }

    Guardar_Itens(gaveta: Text, itens: Object) from "Federal.@.server_tools.Guardar_Itens" {
        codes SUCESSO<0>, DEMORA<1>
    }

    MinhaRotina() from "Federal.@.Lenhador.minha_rotina" {
        codes SUCESSO<0>, FERRAMENTA_GASTA<1>, OUTRA_FALHA<2>
    }

    // Proc-bloco parametrizado
    // home_destino: &Text → placeholder ref
    // gaveta_guardar: Text → placeholder lit
    Ferramenta_Gasta(home_destino: &Text, gaveta_guardar: Text) {
        exec Teleportar(home=&home_destino) {
            case SUCESSO:
                exec Guardar_Itens(gaveta=gaveta_guardar, itens=["diamond_axe"]) {
                    pass SUCESSO, DEMORA
                }
            pass CANCELADO, SUCESSO
        } while(DEMORA)
    }
    // Códigos de saída inferidos: CANCELADO, SUCESSO
}

vars {
    resultado:            Number
    home_machados_gastos: Text
    outra_home:           Text
}

exec MinhaRotina() >> resultado {
    case FERRAMENTA_GASTA: @Ferramenta_Gasta(home_destino=&home_machados_gastos, gaveta_guardar="slot_a")
    case OUTRA_FALHA:      @Ferramenta_Gasta(home_destino=&outra_home, gaveta_guardar="slot_b")
    pass SUCESSO, CANCELADO
}
```

**Resultado após expansão pelo desugar (AST canônica equivalente):**

```gnj
exec MinhaRotina() >> resultado {
    case FERRAMENTA_GASTA:
        exec Teleportar(home=&home_machados_gastos) {
            case SUCESSO:
                exec Guardar_Itens(gaveta="slot_a", itens=["diamond_axe"]) {
                    pass SUCESSO, DEMORA
                }
            pass CANCELADO, SUCESSO
        } while(DEMORA)
    case OUTRA_FALHA:
        exec Teleportar(home=&outra_home) {
            case SUCESSO:
                exec Guardar_Itens(gaveta="slot_b", itens=["diamond_axe"]) {
                    pass SUCESSO, DEMORA
                }
            pass CANCELADO, SUCESSO
        } while(DEMORA)
    pass SUCESSO, CANCELADO
}
```

Duas cópias autônomas, sem dicionário intermediário no Jinja2 gerado.

---

## Tipo `Object` em proc-blocos

O exemplo acima usa `itens=["diamond_axe"]` — uma lista literal. O tipo `Object` foi
implementado no compilador e no motor `code/genjin.jinja2` (B-018, concluído em 2026-05-03).

Regras de uso de `Object` em proc-blocos:
- Permitido como tipo de parâmetro lit: `gaveta_guardar: Object`
- Proibido como tipo de parâmetro ref: `~~gaveta_guardar: &Object~~`
- Proibido em `vars` do programa
- O valor é emitido pelo transpiler como literal Jinja2 opaco, sem transformação

---

## Impacto no compilador (resumo)

Ver `ia/decisions.md` DEC-003 e `ia/backlog-items/B-017.md` (S10-T03) para o detalhamento
completo. Resumo:

| Fase | Mudança |
|---|---|
| `scanner.py` | zero |
| `parser.py` | `ProcBlockNode`, dois passos em `_parse_procs`, bifurcação em `_parse_proc_decl`, `declared_vars` aumentado, inferência de `inferred_codes` (~130 linhas) |
| `desugar.py` | DFS anti-recursão, expansão com deep clone + visitor, filtro de proc-blocos (~90 linhas) |
| `transpiler.py` | zero |
| `ast_io.py` | serialização de `ProcBlockNode` (~30 linhas) |

---

## Pendências e questões abertas

1. **Implementação no compilador** — B-019 (parser) e B-020 (desugar): ver itens de backlog
2. **Highlight VS Code** — `ProcBlockNode` precisará de regra no `genjin.tmLanguage.json` (sprint separada)
3. **CLI `--desugar`** — avaliar se a expansão de proc-blocos deve ser inspecionável via CLI
4. **Proc-blocos sem parâmetros** — caso degenerado válido (bloco fixo sem customização)?
   Tecnicamente sim pela spec, mas sem exemplo ainda.
