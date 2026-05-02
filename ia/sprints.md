# Sprints - Consolidador

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-02

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

- Status: em andamento
- Data de início: 2026-05-02
- Foco: B-017 — Proc-blocos: blocos reutilizáveis com parâmetros de transpilação (pesquisa e proposta)
- Itens: B-017
- Prioridade PO dos itens: 1 (crítica)
- Risco da sprint: médio (2.0)
- Arquivo detalhado: [ia/sprints/SPR-2026-10.md](sprints/SPR-2026-10.md)


## Template sintetico para novas sprints

### SPR-YYYY-NN

- Status:
- Foco:
- Prioridade PO dos itens:
- Risco da sprint:
- Arquivo detalhado: ia/sprints/SPR-YYYY-NN.md
