# Manifesto do agente — Login Todo

## Tecnologias

- Frontend: React, TypeScript, Vite e Material UI.
- Backend: FastAPI, SQLAlchemy, SQLite, PyJWT e pwdlib.
- Execução: Docker Compose.

## Comandos permitidos

```powershell
docker compose up --build
docker compose run --rm backend python -m pytest
docker compose run --rm frontend npm run build
docker compose down
```

## Portas

- Frontend: 5173
- Backend: 8001 (container: 8000)

## Arquivos-chave

- `backend/app/main.py`: rotas, autenticação, banco e regras de negócio.
- `frontend/src/pages/`: telas de login e dashboard.
- `frontend/src/components/`: componentes reutilizáveis de layout, tema e Todo.
- `frontend/src/services/api.ts`: contratos HTTP do frontend.
- `frontend/src/theme/palettes.ts`: paletas e seus papéis de cor.
- `compose.yaml`: serviços e volumes.

## Regras

- Cada tarefa pertence ao usuário do token; nunca aceite `user_id` do frontend.
- Senhas são hash; nunca persistir ou registrar senha em texto puro.
- Não incluir segredos no frontend ou no Git.
- Ao alterar contrato HTTP, atualizar `frontend/src/services/api.ts` e os testes.
