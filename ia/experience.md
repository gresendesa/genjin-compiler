# Experience - Retrospectiva e Memoria de Processo

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-03 (EXP-002 adicionado — SPR-2026-12)

## Objetivo

Registrar problemas observados no processo de desenvolvimento, suas causas e como evitar recorrencia.

## Formato de registro

- ID:
- Data:
- Contexto:
- Problema:
- Impacto:
- Causa raiz:
- Acao corretiva:
- Acao preventiva:
- Status: aberto | mitigado | resolvido | obsoleto
- Owner:

## Registros

---

### EXP-001 — Gap `Object` resolvido fora de sprint formal pelo PO

- **ID:** EXP-001
- **Data:** 2026-05-03
- **Contexto:** B-018 (tipo `Object`) foi identificado como gap durante a validação do exemplo
  ilustrativo do B-017 (S10-T02). O item foi criado como backlog pendente com dependência
  externa documentada ("Requer ação manual do owner").
- **O que aconteceu:** O PO implementou diretamente (scanner, parser, transpiler e
  `code/genjin.jinja2`) sem passar por sprint formal. O LenhadorNEO foi usado como caso de
  teste e está funcionando.
- **Impacto:** Positivo — gap resolvido mais rápido. B-019 e B-020 já podem ser implementados
  sem bloqueio.
- **Aprendizado:** Itens de baixo risco técnico com implementação direta pelo PO podem ser
  resolvidos fora do ciclo de sprint sem perda de qualidade, desde que documentados no backlog
  após a conclusão.
- **Ação preventiva:** Ao criar itens de backlog com dependência de "ação manual do owner",
  deixar explícito no campo `Status` que pode ser resolvido assincronamente pelo PO — e incluir
  critério de aceite que o PO possa marcar diretamente.
- **Status:** resolvido
- **Owner:** gresendesa (PO)

---

### EXP-002 — `evaluation='literal'` vs `'placeholder'` em ArgumentoNode de proc-bloco

- **ID:** EXP-002
- **Data:** 2026-05-03
- **Contexto:** SPR-2026-12, implementação de B-020 (`_substitute_params` no desugar).
- **Problema:** O parser emitia `evaluation='literal'` para argumentos bare-IDENT no corpo de
  proc-blocos (`msg=msg`), enquanto `_substitute_params` só substituía `'reference'` e
  `'placeholder'`. Resultado: parâmetros literais não eram substituídos após expansão.
- **Impacto:** 5 testes de TestProcBlockDesugar falhando (substituição de parâmetros
  sem efeito).
- **Causa raiz:** O parser não distinguia IDENT-como-placeholder (parâmetro do proc-bloco
  enclosing) de IDENT-como-literal. Ambos recebiam `evaluation='literal'`.
- **Ação corretiva:** Adicionado `_pb_param_names: frozenset[str]` como estado de instância
  no Parser. Em `_parse_proc_block_body`, seta esse conjunto antes de parsear o corpo e o
  reseta após. Em `_parse_kwargs`, usa `evaluation='placeholder'` quando o IDENT está em
  `_pb_param_names`.
- **Ação preventiva:** Ao introduzir novos tipos de evaluation na AST, garantir que o
  emitter (parser) e o consumer (desugar/visitor) usem os mesmos valores. Documentar em
  `ia/code.md` os valores válidos de `ArgNode.evaluation`.
- **Status:** resolvido
- **Owner:** agente

---

- **ID:** EXP-003
- **Data:** 2026-05-03
- **Contexto:** SPR-2026-14, B-024 — extensão de `while` inline para múltiplos códigos.
- **Problema:** `_skip_inline_seq` no parser só avançava 1 IDENT dentro de `while(CODE)`.
  Com `while(ERR, OK)`, o skip ficava com o cursor mal posicionado, fazendo o `_parse_program`
  registrar a inline seq duas vezes e falhar com "bloco 'exec' raiz declarado mais de uma vez".
- **Impacto:** 5 novos testes falhando após implementação da feature.
- **Causa raiz:** `_skip_inline_seq` foi criado quando `while` só tinha 1 código. Não foi
  atualizado junto com a gramática ao ampliar para múltiplos.
- **Ação corretiva:** Substituir avanço fixo (`advance × 3`) por loop `while not RPAREN` dentro
  de `_skip_inline_seq`.
- **Ação preventiva:** Sempre que alterar a gramática de um construto (ex.: permitir lista onde
  havia escalar), buscar e atualizar todos os métodos `_skip_*` correspondentes.
- **Status:** resolvido
- **Owner:** agente

---

### EXP-004 — Átomo terminal sem `while(DEMORA)` deixa DEMORA borbulhar até bloco raiz

- **ID:** EXP-004
- **Data:** 2026-05-03
- **Contexto:** SPR-2026-14, B-023 — refatorar `Troca_Ferramenta` com notação inline.
- **Problema:** O átomo terminal `@Teleportar(home=&home_voltar)` foi escrito sem `while(DEMORA)`.
  Sem o `while`, o código DEMORA do proc vai para `PASS_CODES` do bloco terminal e borbulha
  por toda a cadeia inline. O `LOOP_WHILE` de blocos intermediários absorve apenas o DEMORA
  do _próprio_ proc, não o DEMORA propagado de blocos filhos. DEMORA chegou a `Reseta variáveis`
  que não o declara, causando erro de motor Genjin em runtime.
- **Impacto:** Pipeline `compiler | assembler | indenter` falhava com
  `The codes ['DEMORA'] passed to the block 'Reseta variáveis' must be handled locally`.
- **Causa raiz:** Tradução incorreta do canônico para inline — o canônico tinha
  `} while(DEMORA)` no terminal `Teleportar`; a versão inline omitiu esse `while`.
- **Ação corretiva:** Adicionar `while(DEMORA)` ao átomo terminal:
  `@Teleportar(home=&home_voltar) while(DEMORA)`
- **Ação preventiva:** Ao converter bloco canônico para inline, o átomo terminal **deve**
  replicar todos os `while` do bloco canônico mais interno. O LOOP_WHILE de um bloco
  absorve APENAS o código do próprio proc — nunca o de filhos borbulhados.
- **Status:** resolvido
- **Owner:** agente

