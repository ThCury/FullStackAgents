# Coleção Postman

Importe `fullstack-agents.postman_collection.json` no Postman.

A variável `{{base_url}}` começa com o valor `http://127.0.0.1:8000`. Altere-a
na coleção se a API rodar em outro endereço.

Execute **Criar run do PO** primeiro. O teste da própria request salva
automaticamente o `run_id` retornado na variável `{{run_id}}`, usada pelos GETs de
status, resultado e auditoria.

