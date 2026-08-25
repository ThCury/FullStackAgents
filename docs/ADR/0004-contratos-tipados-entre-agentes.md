# ADR-0004 — Contratos tipados entre agentes

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

Texto livre é flexível, mas não é seguro para decidir automaticamente se uma
história avançou, falhou ou deve ser refeita.

## Decisão

Cada agente terá entradas e saídas tipadas, validadas em runtime. Handoffs levam
IDs de artefatos e dados estruturados. Respostas inválidas podem ser corrigidas por
retry limitado e ficam registradas na auditoria.

## Alternativas consideradas

- Texto livre com parsing: reduz modelos iniciais, mas torna o fluxo frágil.
- Um schema único para todos: parece uniforme, mas viola segregação de interfaces
  e cria muitos campos opcionais.

## Consequências

Roteamento e testes ficam determinísticos. Alterações de contrato precisam de
versionamento e compatibilidade explícita.

