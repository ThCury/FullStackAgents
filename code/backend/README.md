# Backend

Ponte HTTP entre o frontend e o pipeline de agentes (`code/pipeline`). Não
tem lógica própria de negócio - só recebe a demanda, chama
`pipeline.stream.run_pipeline_stream` e transmite os eventos para o frontend
via Server-Sent Events (SSE).

## Como rodar

A key da Anthropic fica em `code/pipeline/.env` (não aqui - ver
`pipeline/README.md`). Este backend só precisa dela indiretamente, através do
pacote `pipeline`.

```bash
cd code
python3 -m venv .venv && source .venv/bin/activate   # se ainda não existir um venv
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Precisa ser executado a partir de `code/` (não de `code/backend/`) para o
import `from pipeline...` funcionar - o pacote `pipeline` é irmão de
`backend`, ambos sob `code/`.

`GET /health` confirma que o servidor subiu. `.env.example` traz os únicos
parâmetros próprios do backend (origem de CORS liberada e porta) - opcionais,
já funcionam com o default para rodar tudo localmente.

## Endpoint

`POST /api/demandas/stream`

Body:
```json
{ "demand": "texto da demanda", "max_revisions": 2 }
```
(`max_revisions` é opcional; sem ele, usa o default do pipeline.)

Resposta: stream SSE (`text/event-stream`), uma linha `data: {...}` por
evento:

- `{"type": "message", "data": {"from_agent", "to_agent", "content", "ts"}}`
  para cada nova troca entre agentes, na ordem em que acontecem.
- `{"type": "done", "data": {"status", "stories", "decisions", "qa_results"}}`
  uma única vez, ao final da execução.
- `{"type": "error", "data": "mensagem"}` se o pipeline falhar no meio da
  execução.

O frontend consome isso com `fetch` + `ReadableStream` (não `EventSource`,
que não suporta POST com corpo).
