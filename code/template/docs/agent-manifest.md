# Manifesto do agente — Login Todo

## Tecnologias

- Frontend: React, TypeScript, Vite e Material UI.
- Backend: FastAPI MVC, SQLAlchemy, PostgreSQL, PyJWT e pwdlib.
- Execução: Docker Compose.

## Comandos permitidos

```powershell
docker compose up --build
docker compose run --rm -e DATABASE_URL=sqlite:///./test.db backend python -m pytest
docker compose run --rm frontend npm run build
docker compose down
```

## Portas

- Frontend: 5173
- Backend: 8001 (container: 8000)

## Arquivos-chave

- `backend/app/models/`: entidades SQLAlchemy.
- `backend/app/views/`: rotas HTTP.
- `backend/app/controllers/`: regras de negócio.
- `backend/app/database.py`: engine, sessões e inicialização do banco.
- `frontend/src/pages/`: telas de login, tarefas e perfil.
- `frontend/src/components/`: componentes reutilizáveis de layout, tema e Todo.
- `frontend/src/components/profile/ProfileModal.tsx`: edição de nome e e-mail.
- `frontend/src/components/todos/TodoModal.tsx`: criação e edição de tarefas.
- `frontend/src/services/api.ts`: contratos HTTP do frontend.
- `frontend/src/theme/palettes.ts`: paletas e seus papéis de cor.
- `compose.yaml`: serviços e volumes.

## Regras

- Cada tarefa pertence ao usuário do token; nunca aceite `user_id` do frontend.
- Tarefas têm título, descrição, horário opcional e recorrência diária opcional.
- Senhas são hash; nunca persistir ou registrar senha em texto puro.
- Não incluir segredos no frontend ou no Git.
- Ao alterar contrato HTTP, atualizar `frontend/src/services/api.ts` e os testes.
