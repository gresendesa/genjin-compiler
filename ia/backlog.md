# Backlog - Consolidador

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-03 (B-021 concluído — SPR-2026-11)

## Objetivo

Este arquivo e um consolidado sintetico dos itens de backlog.

Detalhes completos de cada item ficam em arquivos dedicados no diretorio ia/backlog-items/.

## Convencao

- Item de backlog: B-XXX
- Arquivo detalhado: ia/backlog-items/B-XXX.md

## Resumo sintetico dos itens

### Concluidos

| ID | Titulo | Prioridade PO | Risco | Arquivo |
|---|---|---|---|---|
| B-001 | Criar primeira versao de ia/architecture.md | 1 (critica) | baixo | [B-001.md](backlog-items/B-001.md) |
| B-002 | Criar primeira versao de ia/code.md | 1 (critica) | baixo | [B-002.md](backlog-items/B-002.md) |
| B-003 | Criar documentacao da linguagem DSL Genjin (.gnj) | 1 (critica) | baixo | [B-003.md](backlog-items/B-003.md) |
| B-004 | Implementar scanner (compiler/scanner.py) | 1 (critica) | medio | [B-004.md](backlog-items/B-004.md) |
| B-005 | Implementar parser (compiler/parser.py) | 2 (alta) | alto | [B-005.md](backlog-items/B-005.md) |
| B-006 | Implementar transpiler (compiler/transpiler.py) | 3 (media) | medio | [B-006.md](backlog-items/B-006.md) |
| B-007 | CLI standalone para cada etapa do compilador | 1 (critica) | medio | [B-007.md](backlog-items/B-007.md) |
| B-008 | Criar script compiler.py (pipeline completo) | 2 (alta) | baixo | [B-008.md](backlog-items/B-008.md) |
| B-009 | Assembler: leitura de template via stdin (pipe) | 2 (alta) | medio | [B-009.md](backlog-items/B-009.md) |
| B-010 | Transpiler: ajustar import de genjin.jinja2 para notação DottedLoader | 1 (critica) | baixo | [B-010.md](backlog-items/B-010.md) |
| B-011 | Extensão VS Code para suporte à linguagem Genjin | (a definir) | baixo | [B-011.md](backlog-items/B-011.md) |
| B-012 | Parser: enforçar ordem `as` antes de `>>` no bloco exec | 1 (crítica) | baixo | [B-012.md](backlog-items/B-012.md) |
| B-013 | Parser: remover keyword `proc` das declarações dentro de `procs { }` | 1 (crítica) | baixo | [B-013.md](backlog-items/B-013.md) |
| B-014 | Parser: tornar a ordem dos blocos `vars`, `procs`, `exec` flexível | 1 (crítica) | médio | [B-014.md](backlog-items/B-014.md) |
| B-015 | Compilador: suporte à notação inline `@proc()` (açúcar sintático) | 1 (crítica) | alto | [B-015.md](backlog-items/B-015.md) |
| B-016 | Extensão VS Code: suporte à sintaxe inline `@proc()` e keyword `when` | 1 (crítica) | baixo | [B-016.md](backlog-items/B-016.md) |
| B-017 | Proc-blocos: blocos reutilizáveis com parâmetros de transpilação | 1 (crítica) | médio-alto | [B-017.md](backlog-items/B-017.md) |
| B-018 | Tipo `Object`: literais estruturados em parâmetros de procedimento | 1 (crítica) | médio | [B-018.md](backlog-items/B-018.md) |
| B-021 | Criar `examples/lenhador.gnj` — script de referência do LenhadorNEO | 1 (crítica) | médio | [B-021.md](backlog-items/B-021.md) |

### Pendentes

| ID | Titulo | Prioridade PO | Risco | Arquivo |
|---|---|---|---|---|
| B-019 | Proc-blocos: extensão do parser (`ProcBlockNode`, dois passos, inferência) | (a definir) | alto | [B-019.md](backlog-items/B-019.md) |
| B-020 | Proc-blocos: expansão no desugar (DFS, clone, visitor, filtro) | (a definir) | médio | [B-020.md](backlog-items/B-020.md) |

### Em andamento

(nenhum)

## Template sintetico para novos itens
