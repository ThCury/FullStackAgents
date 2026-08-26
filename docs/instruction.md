# Instruções para rodar o backend

## Pré-requisitos

- Python 3.11 ou superior;
- uma chave Gemini no arquivo `code/backend/.env`:

```dotenv
GEMINI_API_KEY=sua_chave
```

O provider e modelo do PO são versionados em
`code/backend/config.py`, no mapa `AGENT_LLM_PROFILES`.

## Banco de dados — MongoDB

As runs são persistidas no MongoDB. Sem o banco em execução, a API não sobe; isso
evita executar por engano com dados apenas em memória.

Instale e abra o Docker Desktop. Em seguida, no PowerShell, na raiz do repositório:

```powershell
cd code\backend
docker compose up -d
docker compose ps
```

O status do serviço `mongo` deve aparecer como `running`. Os dados ficam no volume
Docker `mongo_data`, na base `fullstack_agents` e na coleção `runs`; eles continuam
existindo ao parar e iniciar o container novamente.

Se surgir um erro que cite `dockerDesktopLinuxEngine`, o Docker Desktop ainda não
está aberto ou não terminou de iniciar. Abra o aplicativo **Docker Desktop**, aguarde
o status *Engine running* e valide no PowerShell:

```powershell
docker info
```

Depois execute novamente `docker compose up -d`, sempre dentro de
`code\backend`, onde está o arquivo `docker-compose.yml`.

O comando acima sobe todos os serviços definidos no projeto. Hoje há somente o
container `mongo`; quando a API, workers ou outras ferramentas forem
containerizados, eles serão adicionados à seção `services` desse mesmo arquivo e
subirão pelo mesmo comando.

Para consultar os logs caso o Mongo não inicie:

```powershell
docker compose logs mongo
```

Para parar somente o banco, preservando os dados:

```powershell
docker compose stop mongo
```

O endereço, nome da base e tipo de persistência são configurações versionadas em
`code/backend/config.py` (`BACKEND_CONFIG`). O `.env` continua reservado apenas às
chaves de API.

## Rodar a API

No PowerShell:

```powershell
cd code\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/docs` para a documentação interativa.

Confira `http://127.0.0.1:8000/health`. O campo `persistence` deve retornar
`mongo`.

Se a porta `8000` estiver ocupada, use a porta `8010` e atualize a variável
`base_url` da coleção Postman:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

## Testar uma run

Com a API em execução, envie o prompt pelo PowerShell:

```powershell
$body = @{ prompt = "Quero criar um portal para clientes consultarem suas apólices." } | ConvertTo-Json -Compress
$bodyUtf8 = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/runs" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $bodyUtf8
```

A resposta contém o `run_id`. Use-o para consultar o resultado e a auditoria:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/runs"
Invoke-RestMethod "http://127.0.0.1:8000/runs/SEU_RUN_ID?dataset=resume"
Invoke-RestMethod "http://127.0.0.1:8000/runs/SEU_RUN_ID?dataset=full"
Invoke-RestMethod "http://127.0.0.1:8000/runs/SEU_RUN_ID/audit"
```

`dataset=resume` é o padrão e retorna somente o acompanhamento da execução:
status, prompt enviado, resposta recebida, tokens gastos, tempo, modelo, agente e
system prompt. Em caso de falha, o erro vem limitado a 500 caracteres nessa visão.
Use `dataset=full` quando precisar do documento completo da run, incluindo toda a
timeline. O endpoint `/audit` também retorna somente a auditoria completa.

`GET /runs` lista todas as runs de forma ainda mais enxuta: identificador, status,
prévia de até 160 caracteres do prompt, solicitante e horários em Brasília.

## Coleção Postman

Você também pode testar todas as requests importando a
[coleção Postman](Colection/fullstack-agents.postman_collection.json).

Ela possui `POST /runs`, consultas de status, resultado e auditoria. A variável
`{{base_url}}` começa com `http://127.0.0.1:8000`; altere-a se usar outra porta.

## Testes automatizados

Dentro de `code/backend`:

```powershell
python -m pytest -q -p no:cacheprovider
python -m ruff check .
```
