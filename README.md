# FullStack Agents

Projeto de um time de agentes capaz de criar aplicações web a partir de um prompt.
O squad mínimo possui Product Owner, Developer e QA, coordenados por LangGraph,
com backend Python e persistência/auditoria em MongoDB.

O DEV pode criar um projeto novo ou evoluir um projeto existente a partir de uma
cópia isolada e auditável.

## Executar a aplicação completa

O frontend, a API, o MongoDB e o Prometheus fazem parte da mesma stack Docker.
Crie o arquivo de segredos e informe sua chave Gemini:

```powershell
Copy-Item code\backend\.env.example code\backend\.env
```

Depois, entre na pasta executável do projeto e execute:

```powershell
cd code
docker compose up -d --build
docker compose ps
```

Serviços disponíveis:

- aplicação web: `http://localhost:5173`;
- Swagger da API: `http://localhost:8000/docs`;
- métricas da API: `http://localhost:8000/metrics`;
- Prometheus: `http://localhost:9090`.

Os dados do MongoDB, os workspaces gerados e as séries do Prometheus ficam em
volumes Docker. `docker compose down` para a stack sem apagar esses dados.

## Documentação

- [Índice da documentação](docs/README.md)
- [Requisitos funcionais e não funcionais](docs/requisitos.md)
- [Arquitetura e princípios SOLID](docs/arquitetura.md)
- [Architecture Decision Records](docs/ADR/README.md)
- [Como executar o backend](docs/instruction.md)

## Resultado esperado do MVP

```text
Prompt do usuário
      ↓
PO cria backlog e critérios
      ↓
DEV implementa uma história
      ↓
QA executa testes ── reprova ──> DEV corrige
      ↓ aprova
Código + instruções + relatório + auditoria de custo
```

Para cada execução será possível consultar prompts, respostas, origem, destino,
modelo, tokens, custo, timeline e artefatos gerados.
