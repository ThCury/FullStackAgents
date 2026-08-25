# ADR-0007 — Cópia isolada para projetos existentes

**Status:** aceita  
**Data:** 2026-08-25

## Contexto

O DEV precisa criar aplicações do zero e também evoluir repositórios já existentes.
Modificar a origem diretamente compromete a segurança, dificulta auditoria e pode
destruir trabalho local do usuário.

## Decisão

Cada `run` de projeto existente parte de uma revisão autorizada e imutável. O
sistema cria uma cópia de trabalho exclusiva, executa diagnóstico, mudanças e QA
nela, e entrega diff mais metadados de aplicação/reversão. A origem é somente
leitura; no MVP não há `push`, merge ou deploy automático.

## Alternativas consideradas

- Editar diretamente a branch de origem: elimina cópia, mas expõe código e trabalho
  local a alterações não revisadas.
- Exigir fork remoto por execução: isola bem, mas pressupõe credenciais, acesso de
  rede e integração Git antes de o MVP provar seu valor.

## Consequências

O resultado é reversível e auditável, e vários runs podem operar sobre a mesma
revisão sem conflito. Em troca, há custo de disco e o usuário precisa aplicar ou
publicar a mudança resultante.

