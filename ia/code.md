# Code Notes - Mapa Rapido de Arquivos Criticos

Status do documento: ativo
Owner: agente
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-04-26

## Objetivo

Resumo rapido para entender arquitetura em nivel de codigo e acelerar retomada em novas sessoes.

---

## Legenda de Status

| Status | Significado |
|---|---|
| `pronto` | Implementado e funcional. Não alterar sem motivo claro. |
| `intocavel` | Criado manualmente pelo owner. **Nunca modificar.** |
| `vazio-alvo` | Arquivo existente mas sem implementação. É o alvo principal de desenvolvimento. |

---

## Arquivos Críticos

### assembler.py
- **Status:** `pronto`
- **Responsabilidade:** Renderizador Jinja2 genérico. Recebe qualquer template Jinja2 válido e gera o output final. Não tem vínculo com `code/genjin.jinja2` — o template de entrada *pode* importá-lo, mas o assembler não sabe nem depende disso.
- **Entrada:** Template Jinja2 + diretório de templates + variáveis de contexto (via `-v` ou `-f JSON`).
- **Saída:** Arquivo de texto com output renderizado.
- **Delimitadores do projeto:** `{* *}` para blocos (em vez do padrão `{% %}`). Variáveis mantêm `{{ }}`.
- **Classe interna:** `Cortex` — gera identificadores hexadecimais únicos para uso nos templates.
- **Documentação:** `docs/assembler.md`.
- **NUNCA alterar este arquivo.**

---

### code/genjin.jinja2
- **Status:** `intocavel`
- **Responsabilidade:** Motor Genjin. Define macros e constantes usadas pelos templates da DSL.
- **Exports:**
  - `ATTRIBUTE` — todas as chaves da DSL (NAME, TYPE, PROCEDURE, VARIABLE, BLOCK, CASES, LOOP_WHILE, PASS_CODES, OUTPUT_CODES, OUTPUT_CODE, CODE, PARAMETERS, VARIABLES, PROCEDURES, MACRO, DESCRIPTION, CARDINALITY, EVALUATION, EVALUATE_VAR, KEYWORD_ARGS, ID, DEFAULT, VALUE).
  - `STAGE` — estágios de execução (`BEFORE_PROCEDURE`, `AFTER_PROCEDURE`).
  - Macros: `filter_list_objects`, `is_list`, `is_dict`.
- **Criado manualmente pelo owner.** Qualquer alteração requer aprovação explícita do PO.
- **Documentação:** `docs/genjin.md`.

---

### compiler/scanner.py
- **Status:** `pronto`
- **Responsabilidade:** Etapa 1 do compilador — análise lexográfica.
- **Entrada:** String com código-fonte da DSL Genjin (`.gnj`).
- **Saída:** Lista de `Token` (dataclass com `type: TokenType`, `value: str`, `line: int`).
- **Classes principais:** `TokenType` (enum), `Token` (dataclass), `Scanner`, `ScannerError`.
- **Testes:** `tests/scanner/test_scanner.py` (65 testes).

---

### compiler/parser.py
- **Status:** `vazio-alvo`
- **Responsabilidade:** Etapa 2 do compilador — análise sintática e semântica.
- **Entrada:** Lista de tokens (saída do scanner).
- **Saída:** AST (Abstract Syntax Tree).
- **Nota:** Arquivo existe com docstring de etapa mas sem implementação.

---

### compiler/transpiler.py
- **Status:** `vazio-alvo`
- **Responsabilidade:** Etapa 3 do compilador — transpilação da AST para notação Genjin.
- **Entrada:** AST (saída do parser).
- **Saída:** Template Jinja2 conforme a notação Genjin, pronto para execução pelo `assembler.py`.
- **Nota:** Arquivo existe com docstring de etapa mas sem implementação.

---

### docs/genjin.md
- **Status:** `pronto`
- **Responsabilidade:** Especificação completa da DSL Genjin. Fonte de verdade para o compilador.
- **Conceitos centrais documentados:** ATTRIBUTE, TYPE, CARDINALITY, EVALUATION, VARIABLE, PROCEDURE, OUTPUT_CODE, BLOCK, CASES, LOOP_WHILE, PASS_CODES, cadeia de responsabilidade, célula de operação.

---

### docs/assembler.md
- **Status:** `pronto`
- **Responsabilidade:** Documentação de uso do `assembler.py`. Argumentos, delimitadores e exemplos.

---

## Ordem de Implementação Recomendada

```
1. compiler/scanner.py   → produz tokens
2. compiler/parser.py    → produz AST
3. compiler/transpiler.py → produz template Genjin para o assembler
```

O output do transpiler é o contrato de interface com o `assembler.py`. O assembler não deve ser modificado.

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|---|---|---|
| 2026-04-26 | 1.0.0 | Primeira versão. Todos os arquivos críticos mapeados. |
