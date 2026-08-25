# ADR-0005 — Medição centralizada de consumo e custos

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

É obrigatório saber o consumo e o custo de todas as chamadas, inclusive das que
falharam ou forem adicionadas no futuro.

## Decisão

Envolver todo adaptador de LLM com um gateway auditável. Ele registra início e
fim, normaliza tokens, calcula custo com tabela versionada e respeita orçamento.
Quando o provedor informar cobrança efetiva, armazenar valor estimado e faturado.

## Alternativas consideradas

- Cada agente mede sua chamada: duplica código e permite chamadas sem medição.
- Calcular apenas ao final: perde contexto de falhas e impede bloqueio preventivo.

## Consequências

Medição e políticas ficam consistentes para todos os agentes. A tabela de preços
precisa de manutenção e o sistema deve distinguir estimativa de cobrança real.

