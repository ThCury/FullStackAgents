# ADR-0001 — Monólito modular com portas e adaptadores

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

O produto começa com três agentes e precisa evoluir sem acoplar regras de negócio
a frameworks, bancos ou provedores de IA.

## Decisão

Usar um monólito modular Python, organizado em domínio, aplicação, interfaces e
infraestrutura. Dependências externas implementam portas definidas internamente.

## Alternativas consideradas

- Microsserviço por agente: melhora isolamento, mas adiciona rede, deploy e
  consistência distribuída cedo demais.
- Aplicação em uma única camada: inicia rápido, mas mistura fluxo, banco e SDKs.

## Consequências

Deploy e depuração são simples, e testes podem usar fakes. A equipe deve fiscalizar
as fronteiras; módulos no mesmo processo ainda podem se acoplar indevidamente.

