# Template — Login e Todo

Template fullstack para novos projetos criados pelo FullStack Agents. Ele contém
autenticação por JWT e um CRUD de tarefas isolado por usuário.

## Rodar

Copie `.env.example` para `.env` e defina uma chave JWT própria. No PowerShell:

```powershell
Copy-Item .env.example .env
```

Depois:

```powershell
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8001/docs

Para parar os containers, mantendo os dados locais:

```powershell
docker compose down
```

Para remover também os dados SQLite do template:

```powershell
docker compose down -v
```

## Testar e compilar

```powershell
docker compose run --rm backend python -m pytest
docker compose run --rm frontend npm run build
```

## Estrutura

- `frontend/`: React, TypeScript, Vite e Material UI;
- `backend/`: FastAPI, SQLAlchemy, SQLite, JWT e hash de senha;
- `docs/agent-manifest.md`: contexto curto para o agente DEV.
