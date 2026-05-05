# Sprints - Consolidador

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-04 (SPR-2026-18 aberta — B-029 em andamento)

## Objetivo

Este arquivo e um consolidado sintetico das sprints.

Detalhes completos de cada sprint ficam em arquivos dedicados no diretorio ia/sprints/.

## Convencao

- Sprint: SPR-YYYY-NN
- Arquivo detalhado: ia/sprints/SPR-YYYY-NN.md

## Sprints registradas

### SPR-2026-01

- Status: concluida
- Foco: Documentacao da linguagem DSL Genjin (.gnj)
- Itens: B-003
- Prioridade PO dos itens: 1 (critica)
- Risco da sprint: baixo (1.1)
- Arquivo detalhado: [ia/sprints/SPR-2026-01.md](sprints/SPR-2026-01.md)

### SPR-2026-02

- Status: concluida
- Data de encerramento: 2026-04-28
- Foco: Implementacao completa do compilador (scanner, parser, transpiler)
- Itens: B-004, B-005, B-006
- Testes entregues: 167 (0 falhas)
- Risco da sprint: medio (2.33)
- Arquivo detalhado: [ia/sprints/SPR-2026-02.md](sprints/SPR-2026-02.md)


### SPR-2026-03

- Status: concluída
- Data de início: 2026-04-28
- Foco: CLI standalone por etapa + script compiler.py
- Itens: B-007, B-008
- Prioridade PO dos itens: 1 (critica), 2 (alta)
- Risco da sprint: baixo/medio (1.5)
- Arquivo detalhado: [ia/sprints/SPR-2026-03.md](sprints/SPR-2026-03.md)


### SPR-2026-04

- Status: concluída
- Itens: B-009
- Prioridade PO dos itens: 2 (alta)
- Risco da sprint: baixo/médio (1.33)
- Arquivo detalhado: [ia/sprints/SPR-2026-04.md](sprints/SPR-2026-04.md)


### SPR-2026-05

- Status: concluída
- Data de início: 2026-04-28
- Foco: Transpiler — corrigir import de genjin para notação DottedLoader (`"genjin"`)
- Itens: B-010
- Prioridade PO dos itens: 1 (critica)
- Risco da sprint: baixo (1.0)
- Arquivo detalhado: [ia/sprints/SPR-2026-05.md](sprints/SPR-2026-05.md)


### SPR-2026-06

- Status: concluída
- Data de início: 2026-05-01
- Data de encerramento: 2026-05-01
- Foco: Correções de gramática do parser (ordem `as`/`>>`, remoção de `proc`, ordem flexível de blocos)
- Itens: B-013, B-012, B-014
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: baixo/médio (1.33)
- Testes entregues: 287 (0 falhas)
- Arquivo detalhado: [ia/sprints/SPR-2026-06.md](sprints/SPR-2026-06.md)


### SPR-2026-07

- Status: concluída
- Data de início: 2026-05-01
- Data de encerramento: 2026-05-01
- Foco: B-015 Fase 1 — análise técnica da notação inline `@proc()` (açúcar sintático)
- Itens: B-015 (Fase 1)
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: alto
- Decisões: DEC-001 (desugar separado), DEC-002 (sintaxe `when(CODE)`)
- Arquivo detalhado: [ia/sprints/SPR-2026-07.md](sprints/SPR-2026-07.md)


### SPR-2026-08

- Status: concluída
- Data de início: 2026-05-01
- Data de encerramento: 2026-05-01
- Foco: B-015 Fase 2 — implementação completa (`desugar.py`, scanner, parser, testes, docs)
- Itens: B-015 (Fase 2)
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: alto
- Resultado: 341 testes, 0 falhas (+54 novos testes). B-015 concluído.
- Arquivo detalhado: [ia/sprints/SPR-2026-08.md](sprints/SPR-2026-08.md)


### SPR-2026-09

- Status: concluída
- Data de início: 2026-05-02
- Data de encerramento: 2026-05-02
- Foco: B-016 — Extensão VS Code: suporte à sintaxe inline `@proc()` e keyword `when`
- Itens: B-016
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: baixo (1.0)
- Resultado: +1 keyword (`when`), +1 regra highlight (`inline-call`), bump patch 0.1.1
- Arquivo detalhado: [ia/sprints/SPR-2026-09.md](sprints/SPR-2026-09.md)


### SPR-2026-10

- Status: concluída
- Data de início: 2026-05-02
- Data de encerramento: 2026-05-02
- Foco: B-017 — Proc-blocos: blocos reutilizáveis com parâmetros de transpilação (pesquisa e proposta)
- Itens: B-017
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (2.0)
- Resultado: B-017 concluído — spec completa em `docs/proc-blocos.md`, 7 pontos de design avaliados, DEC-003 registrada, impacto estimado (~330 linhas). Spinoff B-018 identificado.
- Arquivo detalhado: [ia/sprints/SPR-2026-10.md](sprints/SPR-2026-10.md)


### SPR-2026-11

- Status: concluída
- Data de início: 2026-05-03
- Data de encerramento: 2026-05-03
- Foco: B-021 — `examples/lenhador.gnj` + fix parser `param: Type[]` com ref implícita
- Itens: B-021
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (1.6)
- Resultado: B-021 concluído — 3 fixes no compilador (TYPE.OBJECT, param plural, case/while borbulhados), lenhador.gnj compilando. 341 testes.
- Arquivo detalhado: [ia/sprints/SPR-2026-11.md](sprints/SPR-2026-11.md)


### SPR-2026-12

- Status: concluída
- Data de início: 2026-05-03
- Data de encerramento: 2026-05-03
- Foco: Proc-blocos — implementação completa (parser + desugar) + `lenhador-sintetico.gnj`
- Itens: B-019, B-020
- Prioridade PO dos itens: 1 (crítica), 2 (alta)
- Risco da sprint: alto (2.5)
- Resultado: B-019 e B-020 concluídos. `ProcBlockNode` parseado + desugar com DFS anti-ciclo + expansão clone+visitor. `lenhador-sintetico.gnj` compilando com saída equivalente. 360 testes, 0 falhas (+19 novos testes).
- Arquivo detalhado: [ia/sprints/SPR-2026-12.md](sprints/SPR-2026-12.md)


### SPR-2026-13

- Status: concluída
- Data de início: 2026-05-03
- Data de encerramento: 2026-05-03
- Foco: Atualizar README.md com estado atual do projeto
- Itens: B-022
- Prioridade PO dos itens: 3 (média)
- Risco da sprint: baixo (1.0)
- Resultado: README.md reescrito — pipeline completo, estrutura do repositório, features, exemplos validados.
- Arquivo detalhado: [ia/sprints/SPR-2026-13.md](sprints/SPR-2026-13.md)


### SPR-2026-14

- Status: concluída
- Data de início: 2026-05-03
- Data de encerramento: 2026-05-03
- Foco: Fix `while` inline (múltiplos códigos + borbulhados) + refatorar `Troca_Ferramenta` com inline
- Itens: B-024, B-023
- Prioridade PO dos itens: 1 (crítica), 1 (crítica)
- Risco da sprint: médio (1.5)
- Resultado: 366 testes (0 falhas); +6 novos testes; proc-block com corpo inline suportado
- Arquivo detalhado: [ia/sprints/SPR-2026-14.md](sprints/SPR-2026-14.md)


### SPR-2026-15

- Status: concluída
- Data de planejamento: 2026-05-03
- Data de início: 2026-05-03
- Data de encerramento: 2026-05-03
- Foco: B-025 — Fix `get_unhandled_codes_recursively` (código borbulhando além do LOOP_WHILE)
- Itens: B-025
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (1.5)
- Resultado: fix aplicado ao `genjin.jinja2` oficial; `test.gnj` e `lenhador-sintetico.gnj` compilando sem erro.
- Arquivo detalhado: [ia/sprints/SPR-2026-15.md](sprints/SPR-2026-15.md)


### SPR-2026-16

- Status: concluída
- Data de planejamento: 2026-05-03
- Data de início: 2026-05-03
- Foco: B-026 Fatia A — suite de testes `genjin.jinja2`: fundação + sentinels EXP-005
- Itens: B-026 (Fatia A)
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (2.0)
- Arquivo detalhado: [ia/sprints/SPR-2026-16.md](sprints/SPR-2026-16.md)

### SPR-2026-17

- Status: concluída
- Data de planejamento: 2026-05-04
- Data de início: 2026-05-04
- Data de encerramento: 2026-05-04
- Foco: B-027 — Literais de coleção `[...]`/`{...}` como argumentos `Object`
- Itens: B-027
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (2.0)
- Testes: 417 passando, 0 falhas (+18 testes novos)
- Arquivo detalhado: [ia/sprints/SPR-2026-17.md](sprints/SPR-2026-17.md)

### SPR-2026-18

- Status: em andamento
- Data de início: 2026-05-04
- Foco: B-029 — Importação de proc-blocos de arquivos .gnj externos
- Itens: B-028 (estudo, concluído), B-029 (implementação)
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (2.0)
- Testes: 434 passando, 0 falhas (+17 testes novos)
- Arquivo detalhado: [ia/sprints/SPR-2026-18.md](sprints/SPR-2026-18.md)

### SPR-YYYY-NN

- Status:
- Foco:
- Prioridade PO dos itens:
- Risco da sprint:
- Arquivo detalhado: ia/sprints/SPR-YYYY-NN.md
