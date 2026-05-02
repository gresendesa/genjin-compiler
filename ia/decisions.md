# Decisions - Memoria e Governanca

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-02

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

---

### DEC-003 — Proc-blocos: sintaxe, semântica e estratégia de expansão

- **ID:** DEC-003
- **Data:** 2026-05-02
- **Status:** proposta (aprovada para spec — implementação em sprint futura)
- **Sprint:** SPR-2026-10 (B-017)
- **Contexto:** B-017 propõe proc-blocos — sub-programas reutilizáveis declarados em `procs`
  com parâmetros de transpilação (substituídos em tempo de compilação, não em runtime). O padrão
  foi identificado no `code/Federal/@/Lenhador.jinja2` onde dicionários Jinja2 (`BLOCOS_TRATAMENTO`)
  servem como biblioteca de blocos. A proposta substitui esse padrão manual por expansão
  automática no compilador.

- **Decisão (7 pontos):**

  1. **Distinção sintática:** ausência de `from` + corpo `{ exec ... }` identifica o proc-bloco.
     Sem novo token necessário no scanner. O parser bifurca em `_parse_proc_decl`: `from` →
     `ProcDeclNode`; `{` → `ProcBlockNode`.

  2. **Parâmetros de transpilação:** reutilizar convenção `&` existente — `param: &Type` é
     placeholder ref (substituído por nome de variável); `param: Type` é placeholder lit
     (substituído por valor literal). Sintaxe idêntica à declaração de parâmetros de procs
     normais — nenhum nó de parâmetro novo.

  3. **Variável de resultado:** o `exec` mais externo do corpo do proc-bloco **não pode declarar
     `>>`**. A variável é herdada do contexto do ponto de chamada (mesmo mecanismo de herança já
     existente na linguagem). `>>` em blocos internos aninhados é permitido normalmente.

  4. **Códigos de saída:** inferência automática — os `pass_codes` do bloco raiz interno são os
     códigos de saída do proc-bloco. Sem sintaxe `codes { }` no proc-bloco. O parser infere
     `inferred_codes` após parsear o corpo e os armazena em `ProcBlockNode`.

  5. **Detecção de recursão:** DFS no início de `desugar()` sobre grafo de dependência entre
     proc-blocos. Ciclo detectado → `DesugarError` com caminho. Ordem topológica resultante
     define ordem de expansão (folhas primeiro).

  6. **Fase de expansão:** `desugar.py` — mesma fase que expande `@proc()` (B-015). O desugar
     distingue pelo tipo do nó alvo: `ProcDeclNode` → expansão B-015; `ProcBlockNode` →
     clonagem + substituição de parâmetros.

  7. **Substituição de parâmetros:** deep clone da AST do bloco (`copy.deepcopy`) + visitor
     recursivo que percorre `ExecBlockNode → CaseNode → ExecBlockNode` substituindo `ArgNode`
     cujos valores batem com placeholders. AST original do proc-bloco permanece imutável.

- **Impacto no compilador:**

  | Fase | Mudança |
  |---|---|
  | `scanner.py` | zero (B-017) |
  | `parser.py` | `ProcBlockNode`, dois passos em `_parse_procs`, bifurcação em `_parse_proc_decl`, `declared_vars` aumentado com params, inferência de `inferred_codes` (~130 linhas) |
  | `desugar.py` | DFS anti-recursão, expansão com deep clone + visitor, filtro de proc-blocos em `procedures` (~90 linhas) |
  | `transpiler.py` | zero — recebe apenas AST canônica após desugar |
  | `ast_io.py` | serialização/desserialização de `ProcBlockNode` (~30 linhas) |
  | Testes | ~80-100 novos casos |

- **Arquivos afetados:**
  - `compiler/parser.py` — `ProcBlockNode`, `_parse_procs`, `_parse_proc_decl`
  - `compiler/desugar.py` — DFS, expansão, filtro
  - `compiler/ast_io.py` — novo nó
  - `docs/language.md` — nova seção "Proc-Blocos"
  - `docs/proc-blocos.md` — especificação preliminar (criada nesta sprint)

- **Revisão futura:**
  - Avaliar se proc-blocos devem aparecer em `procedures` do Jinja2 gerado (hoje: filtrados fora)
    para fins de documentação/inspeção do programa
  - Avaliar suporte a proc-blocos sem parâmetros (bloco fixo reutilizável sem customização)
