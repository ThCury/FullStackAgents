# ADR-0003 — MongoDB e auditoria append-only

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

Prompts, respostas, handoffs e metadados variam por provedor e precisam ser
consultados como uma timeline confiável.

## Decisão

Usar MongoDB para estado e projeções. Mudanças relevantes também geram eventos
append-only com sequência por `run`. Correções acrescentam eventos; não reescrevem
o histórico. Payloads grandes poderão migrar a object storage mantendo URI e hash.

## Alternativas consideradas

- PostgreSQL: oferece relações e transações fortes, mas exige mais adaptação para
  payloads heterogêneos; continua uma opção futura válida.
- Apenas logs de arquivo: simples, porém fraco para consulta, retenção e acesso
  concorrente.

## Consequências

O esquema evolui com facilidade e a consulta por execução é direta. Índices,
validação de schema, retenção e reconciliação tornam-se obrigatórios para evitar
documentos inconsistentes e crescimento sem controle.

