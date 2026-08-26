# Documentação — FullStack Agents

Este diretório descreve o produto antes da implementação. A proposta é um MVP de
um time de agentes que transforma um prompt em uma aplicação web, mantendo todo o
fluxo auditável.

## Leitura recomendada

1. [Requisitos](requisitos.md) — o que o sistema deve fazer e como validar.
2. [Arquitetura](arquitetura.md) — componentes, fluxo, dados e aplicação de SOLID.
3. [Modelo de dados MongoDB](modelo-dados-mongodb.md) — auditoria de mensagens,
   chamadas LLM e fluxo.
4. [Plano do backend inicial](plano-backend-po.md) — PO com LangGraph, sem DEV/QA.
5. [ADRs](ADR/README.md) — por que as principais decisões foram tomadas.

## Testar a API

A [coleção Postman](Colection/README.md) contém as requests do backend e usa a
variável `{{base_url}}` para o endereço da API.

## Escopo do MVP

- três papéis obrigatórios: Product Owner, Developer e QA;
- orquestração do fluxo com LangGraph;
- API e serviços em Python;
- persistência e auditoria em MongoDB;
- criação de projetos novos ou evolução de projetos existentes em workspace isolado;
- ciclo de correção `DEV -> QA -> DEV` com limite configurável;
- consulta de prompts, respostas, destinatários, tokens e custos.

## Fora do MVP

- vários agentes do mesmo papel trabalhando em paralelo;
- deploy automático em produção;
- treinamento de modelos;
- cobrança financeira do usuário;
- execução sem limites de código gerado;
- edição colaborativa em tempo real.

## Convenções

- `run`: uma solicitação completa do usuário;
- `agent call`: uma chamada de um agente ao modelo;
- `handoff`: passagem de trabalho entre agentes;
- `artifact`: arquivo ou relatório produzido;
- `workspace`: diretório isolado no qual o app é gerado;
- `timestamp`: instante técnico em UTC, no formato ISO 8601;
- `brasil_datetime`: o mesmo instante no fuso `America/Sao_Paulo`, usado como
  horário principal nas telas, relatórios e auditorias humanas;
- valores monetários são armazenados como `Decimal128`, nunca `float`.
