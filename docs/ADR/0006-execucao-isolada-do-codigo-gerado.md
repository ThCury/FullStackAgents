# ADR-0006 — Execução isolada do código gerado

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

O DEV produz código não confiável e o QA precisa executá-lo. Rodar esse código na
API expõe arquivos, credenciais, rede e disponibilidade do serviço.

## Decisão

Executar build e testes em sandbox/container separado, sem segredos, com rede
desabilitada por padrão, filesystem confinado e limites de CPU, memória e tempo.
O executor aceita operações conhecidas, nunca um comando arbitrário vindo do LLM.

## Alternativas consideradas

- Subprocesso local: útil somente no desenvolvimento, com isolamento insuficiente.
- Não executar código: mais seguro, mas impede evidência real de QA.

## Consequências

Reduz-se o impacto de código malicioso ou defeituoso. A operação exige imagens,
limpeza de recursos, quotas e políticas específicas por linguagem.

