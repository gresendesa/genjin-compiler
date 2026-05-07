# Architecture - Macrosoft Dev

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-06 (B-031: pyproject.toml, compiler/config.py, API pública, assembler.render())

## Visão Geral

O projeto implementa um **compilador para a linguagem DSL Genjin**. O objetivo final é permitir que código escrito numa notação de alto nível seja traduzido para templates Jinja2 conformes com o motor Genjin (`code/genjin.jinja2`), que por sua vez são executados pelo assembler (`assembler.py`) para gerar o output final.

### Restrições arquiteturais fixas

| Componente | Restrição |
|---|---|
| `code/genjin.jinja2` | **INTOCÁVEL.** Motor Genjin criado manualmente pelo owner. Nenhuma modificação é permitida. |
| `assembler.py` | **Refatorado em B-031 (SPR-2026-20) com aprovação do PO.** CLI preservada. Núcleo extraído como `render()` pública. Alterar apenas com autorização do PO. |

---

## Componentes

### 1. assembler.py — Motor de Execução

- **Responsabilidade:** Renderizar templates Jinja2 a partir da linha de comando. É um renderizador Jinja2 genérico.
- **Status:** Pronto e funcional. **Refatorado em B-031**: adicionada função pública `render(template_str, loader, context, delimiters)`. CLI permanece inalterada.
- **Entrada (CLI):** Um arquivo de template Jinja2 (ponto de entrada) + diretório de templates + variáveis de contexto.
- **Entrada (API):** `template_str: str`, `loader: BaseLoader | None`, `context: dict`, `delimiters: dict`.
- **Saída:** Arquivo de texto com o output renderizado (CLI) ou string (API).
- **Relação com genjin.jinja2:** Nenhuma dependência direta. O template de entrada *pode* importar `code/genjin.jinja2`, mas o assembler não sabe nem se importa com isso. Ele renderiza qualquer template Jinja2 válido.
- **Delimitadores deste projeto:** `{* *}` para blocos (em vez do padrão `{% %}`). Variáveis mantêm `{{ }}`.
- **Documentação:** `docs/assembler.md`.

### 2. code/genjin.jinja2 — Motor Genjin (INTOCÁVEL)

- **Responsabilidade:** Definir as macros e atributos da DSL Genjin usados em templates.
- **Status:** Pronto. Criado manualmente pelo owner. **Não deve ser modificado.**
- **Entrada:** Importado por templates Jinja2 via `{* import ... *}` ou `{* from ... import ... *}`.
- **Exports principais:**
  - `ATTRIBUTE` — dicionário com todas as chaves da DSL (NAME, TYPE, PROCEDURE, BLOCK, CASES, etc.).
  - `STAGE` — dicionário de estágios de execução.
  - Macros utilitárias: `filter_list_objects`, `is_list`, `is_dict`.
- **Localização:** `code/genjin.jinja2`.

### 3. compiler/scanner.py — Scanner (Etapa 1)

- **Responsabilidade:** Análise lexográfica do código-fonte da DSL Genjin.
- **Status:** Vazio. **Alvo de implementação.**
- **Entrada:** String com código-fonte da DSL Genjin.
- **Saída:** Lista de tokens.

### 4. compiler/parser.py — Parser (Etapa 2)

- **Responsabilidade:** Análise sintática e semântica a partir da lista de tokens.
- **Status:** Vazio. **Alvo de implementação.**
- **Entrada:** Lista de tokens (saída do scanner).
- **Saída:** AST (Abstract Syntax Tree).

### 5. compiler/transpiler.py — Transpiler (Etapa 3)

- **Responsabilidade:** Geração de código Jinja2 conforme a notação Genjin a partir da AST.
- **Status:** Vazio. **Alvo de implementação.**
- **Entrada:** AST (saída do parser).
- **Saída:** Template Jinja2 pronto para ser executado pelo `assembler.py` usando `code/genjin.jinja2`.

---

## Fluxo de Dados

```
Código-fonte DSL
       │
       ▼
┌─────────────────┐
│  scanner.py     │  Etapa 1: análise lexográfica
│  (a implementar)│  Saída: lista de tokens
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  parser.py      │  Etapa 2: análise sintática/semântica
│  (a implementar)│  Saída: AST
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│resolve_imports  │  Etapa 2.7: resolução de importações
│.py (SPR-2026-18)│  Substitui ProcImportNode por ProcBlockNode concretos
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  transpiler.py  │  Etapa 3: transpilação
│  (a implementar)│  Saída: template Jinja2 (notação Genjin)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  assembler.py   │  Motor de execução (pronto, NÃO ALTERAR)
│  (pronto)       │  Usa code/genjin.jinja2 como runtime
└────────┬────────┘
         │
         ▼
     Output final
```

---

## Contratos de Interface

### Scanner → Parser
- **Formato:** Lista de tokens (estrutura a ser definida em scanner.py).
- **Restrição:** O parser não deve importar nenhum módulo externo ao projeto.

### Parser → Transpiler
- **Formato:** AST (estrutura a ser definida em parser.py).
- **Restrição:** A AST deve representar fielmente a semântica da DSL Genjin conforme `docs/genjin.md`.

### Transpiler → Assembler
- **Formato:** Arquivo de template Jinja2 com delimitadores `{* *}` para blocos.
- **Restrição:** O template gerado deve ser executável pelo `assembler.py` sem modificações.
- **Nota:** O template gerado *deve* importar `code/genjin.jinja2` para usar as macros e atributos da DSL Genjin, mas o assembler em si é agnóstico a isso.

---

## Orientação de Desenvolvimento do Compilador

1. O desenvolvimento do compilador (`compiler/`) é orientado inteiramente à geração de código que será executado pelo `assembler.py`.
2. O `assembler.py` é um renderizador Jinja2 genérico — ele não conhece nem depende do `code/genjin.jinja2`.
3. O output do transpiler deve ser um template Jinja2 válido que importe `code/genjin.jinja2` para usar as macros da DSL.
4. A especificação completa da DSL está em `docs/genjin.md`.
5. Qualquer dúvida sobre o contrato de saída deve ser resolvida consultando `code/genjin.jinja2` e `docs/assembler.md`.
6. **`code/genjin.jinja2` nunca deve ser alterado.** Adaptações devem ser feitas no compilador.

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|---|---|---|
| 2026-04-26 | 1.0.0 | Primeira versão. Componentes, fluxo e contratos documentados. |
| 2026-05-04 | 1.1.0 | SPR-2026-18: nova fase `ResolveImports` inserida entre Parser e Desugar. Pipeline: `Scanner → Parser → ResolveImports → Desugar → Transpiler → Assembler`. Novo arquivo `compiler/resolve_imports.py`. `ProcImportNode` temporário na AST entre Parser e ResolveImports. `--import-base` na CLI. |
| 2026-05-06 | 1.2.0 | SPR-2026-20 (B-031): pacote pip `genjin-compiler`. Novos componentes: `compiler/config.py` (`CompilerConfig`, `GnjSourceResolver`, `FilesystemGnjResolver`); `compiler/__init__.py` expõe `compile_gnj()`. `assembler.py` refatorado: `render()` pública + `_make_env()` interna; CLI preservada. `compiler/resolve_imports.py`: novo parâmetro `gnj_resolver`. `compiler/transpiler.py`: `Transpiler(ast, template_name)`. Restrição `assembler.py NÃO ALTERAR` revogada com aprovação do PO. |
