"""Contrato de scaffold entregue ao Dev Agent.

Por que existe (ADR-06 + §11 da arquitetura)
--------------------------------------------
Codegen 100% autônomo é o risco que mais afunda esta trilha. A mitigação é
reduzir a superfície de geração: nós fixamos a stack, a estrutura de pastas e as
convenções; o Dev Agent preenche telas, endpoints e schemas.

Continua sendo "escreve o código" — com ~20% da superfície em vez de 100%, e sem
a variabilidade de cada ciclo reinventar a arquitetura do app gerado.

Este texto vai para o prompt do Dev. Mantenha-o **estável**: ele é parte do
prefixo cacheável. Mudança aqui invalida o cache de todas as chamadas do Dev.
"""

SCAFFOLD_CONTRACT = """
# Contrato do scaffold — App Rivexx

A aplicação gerada segue esta estrutura. Não a reinvente; preencha-a.

## Stack fixa
- Backend: FastAPI (Python 3.12+), Pydantic v2, Motor (MongoDB async)
- Frontend: React 18 + TypeScript + Vite, CSS Modules
- Banco: MongoDB, database `rivexx_db`
- Testes: pytest (API) e Playwright (UI)

## Estrutura de pastas (caminhos relativos à raiz do workspace)
```
app/backend/routers/<recurso>.py     # APIRouter, um arquivo por recurso
app/backend/models/<recurso>.py      # modelos Pydantic
app/backend/repositories/<recurso>.py# acesso a Mongo, uma classe por coleção
app/backend/tests/test_<recurso>.py  # pytest
app/frontend/src/pages/<Tela>.tsx    # uma página por tela
app/frontend/src/components/         # componentes reutilizáveis
app/frontend/tests/<tela>.spec.ts    # Playwright
```

## Convenções obrigatórias
- Toda rota devolve modelo Pydantic, nunca `dict` cru.
- Erro de validação: HTTP 422 com o nome do campo na mensagem.
- Recurso inexistente: HTTP 404 com mensagem legível para o operador — nunca
  stack trace.
- Todo documento gravado carrega os 4 campos de evidência auditável exigidos
  pelo cliente: `recorded_at`, `recorded_by`, `shift`, `equipment_id`.
- A coleção `audit_log` é append-only. Nunca gere `update` ou `delete` nela.

## Coleções já modeladas (não redefina)
- `nonconformities`, `root_cause_analyses`, `action_plans`, `lots`, `audit_log`
- Genealogia de lote: `lots.parent_lot_ids` (array). Travessia por
  `$graphLookup` — não implemente recursão em Python.

## Frontend
- Mobile-first. O operador registra pelo celular no chão de fábrica.
- Nenhuma tela pode ter rolagem horizontal em viewport de 375px.
- Alvo de toque mínimo de 44px: o operador usa luva.
- Rótulo em português, sem jargão técnico — a interface é operável sem
  treinamento.

## Seed
O banco já vem populado (2 plantas, 3 turnos, ~200 lotes com genealogia, ~50 NCs
históricas). Consulte os dados existentes; não gere seed nem migration de dados.
""".strip()
