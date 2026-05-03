# Experience - Retrospectiva e Memoria de Processo

Status do documento: ativo
Owner: gresendesa
Data de criacao: 2026-04-08
Ultima atualizacao: 2026-05-03

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
