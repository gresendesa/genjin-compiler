# Decisions - Memoria e Governanca

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-01

## Objetivo

Registrar historico de decisoes sobre a arquitetura da memoria e o processo de governanca deste workspace.

## Formato de registro

- ID: DEC-XXX
- Data:
- Status: proposta | aprovada | substituida | obsoleta
- Contexto:
- Decisao:
- Impacto:
- Arquivos afetados:
- Revisao futura:

## Historico

---

### DEC-001 — Fase de desaçucaramento separada no compilador

- **ID:** DEC-001
- **Data:** 2026-05-01
- **Status:** aprovada
- **Contexto:** B-015 introduz açúcar sintático (`@proc()`, `@proc()::CODE`) que precisa ser expandido para AST canônica antes da transpilação. A inferência automática de `pass` nas expansões requer acesso ao contexto do nó pai da AST, o que torna a resolução inline durante o parser (descent recursivo) complexa e acoplada.
- **Decisão:** Adicionar `compiler/desugar.py` como nova fase entre o parser e o transpiler. O parser pode emitir nós de açúcar (`InlineExecNode` etc.) que o desugar transforma em nós canônicos (`ExecBlockNode`, `CaseNode` etc.). O transpiler permanece inalterado.
- **Pipeline resultante:** `Source → Scanner → Parser → Desugar → Transpiler → Assembler`
- **Impacto:** Um módulo novo (`compiler/desugar.py`). O `compiler.py` (pipeline) precisa chamar a fase de desugar. O transpiler não é alterado.
- **Arquivos afetados:** `compiler/desugar.py` (novo), `compiler.py`, `compiler/__init__.py`, `ia/architecture.md`
- **Revisão futura:** Avaliar se o desugar deve ser exposto como etapa CLI separada (--desugar flag) após a implementação.

---

### DEC-002 — Sintaxe `when(CODE)` para encadeamento inline (Tipo 2)

- **ID:** DEC-002
- **Data:** 2026-05-01
- **Status:** aprovada
- **Contexto:** B-015 define dois tipos de notação inline. O Tipo 2 requer um "código de encadeamento" — quando o proc retorna esse código, o próximo bloco da sequência é executado. A proposta original usava `::CODE` (ex: `@proc()::OK`). A análise técnica (S7-T03/T06) identificou que `::` conflita com o operador de escopo/tipo de C++/Rust/Haskell, causando risco de confusão.
- **Decisão:** Adotar `when(CODE)` como sintaxe oficial do encadeamento. Quando `while` também está presente, `when` vem depois (ordem: `[>>] [while(W)] when(CODE)`). Semântica: o bloco executa, repete em `while(W)`, e quando `when(CODE)` ocorre prossegue ao próximo bloco; os demais códigos são passados.
- **Impacto:** Scanner recebe `KW_WHEN`. Parser reconhece `when(IDENT)` em posição de inline atom. Não afeta a forma canônica nem o transpiler.
- **Arquivos afetados:** `compiler/scanner.py` (novo token `KW_WHEN`), `compiler/parser.py` (parsing de inline atoms), `compiler/desugar.py` (novo), `docs/language.md`
- **Revisão futura:** Avaliar se `when` deve ser reservado para uso futuro em guards/pattern matching; por ora é exclusivo da notação inline.
