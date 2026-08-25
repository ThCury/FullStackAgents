# ADR-0002 — LangGraph para orquestração

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

O fluxo possui estado, ciclos de correção, limites, checkpoints e futura
intervenção humana.

## Decisão

Usar `StateGraph` do LangGraph como mecanismo de orquestração. Nós chamam casos de
uso e não contêm persistência, prompts ou regras específicas de SDK.

## Alternativas consideradas

- Loop Python manual: adequado ao caminho feliz, mas checkpoints e retomada
  exigiriam infraestrutura própria.
- Sistema de filas desde o início: escalável, porém complexo para o MVP.

## Consequências

Transições ficam explícitas e retomáveis. LangGraph permanece restrito a
`pipeline/`, reduzindo o custo de substituição e facilitando testes do domínio.

