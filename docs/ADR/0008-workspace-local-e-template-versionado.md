# ADR-0008 — Workspace local isolado e template versionado

**Status:** aceita
**Data:** 2026-08-26

## Contexto

O DEV precisa criar projetos em uma área local autorizada e gerar aplicações sem
consumir contexto para reconstruir o mesmo boilerplate em toda run.

## Decisão

Usar `DEV_WORKSPACE_ROOT` como configuração local no `.env`, limitar toda escrita a
subdiretórios derivados dessa raiz e iniciar novos projetos a partir de um template
versionado de login + Todo. Cada projeto derivado terá seu próprio `compose.yaml`
e será compilado/executado em containers isolados.

## Alternativas consideradas

- gerar cada projeto a partir de uma pasta vazia;
- permitir que o agente escreva em qualquer caminho do computador;
- executar o código gerado no processo da API;
- colocar caminho local e modelos no mesmo arquivo versionado.

## Consequências

- reduz consumo de tokens e aumenta consistência entre projetos;
- exige manutenção e versionamento do template;
- o `.env` passa a conter uma configuração local de segurança além de segredos;
- a stack do template precisa ser aprovada antes da implementação do DEV.
