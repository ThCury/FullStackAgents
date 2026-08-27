# Instruções para executar a aplicação

## Pré-requisitos

- Docker Desktop;
- uma chave Gemini no arquivo `code/backend/.env`:

```dotenv
GEMINI_API_KEY=sua_chave

# Pasta local exclusiva onde o DEV criará projetos por run.
# No Docker, este caminho é definido automaticamente como /workspaces.
```

O provider e modelo de cada agente são versionados em
`code/backend/config.py`, no mapa `AGENT_LLM_PROFILES`. O `.env` contém apenas
segredos. Para uso sem Docker, `DEV_WORKSPACE_ROOT` não deve apontar para a raiz
de um repositório existente, pois o DEV cria uma pasta nova para cada run.

## Subir toda a stack

Na raiz do repositório, prepare o segredo e entre na pasta `code`, onde vive toda
a stack executável:

```powershell
Copy-Item code\backend\.env.example code\backend\.env
# Edite code\backend\.env e informe GEMINI_API_KEY.
cd code
docker compose up -d --build
docker compose ps
```

Esse único Compose inicia:

- `frontend`: React compilado e servido pelo Nginx em `http://localhost:5173`;
- `backend`: FastAPI em `http://localhost:8000`;
- `mongo`: persistência interna, sem exposição de porta no host;
- `prometheus`: monitoramento em `http://localhost:9090`.

O frontend encaminha `/api/*` para o backend pela rede interna do Docker. MongoDB,
workspaces dos agentes e Prometheus usam volumes próprios e continuam disponíveis
depois de `docker compose down`.

Se surgir um erro que cite `dockerDesktopLinuxEngine`, o Docker Desktop ainda não
está aberto ou não terminou de iniciar. Abra o aplicativo **Docker Desktop**, aguarde
o status *Engine running* e valide no PowerShell:

```powershell
docker info
```

Depois execute novamente `docker compose up -d`, dentro de `code`, onde está o
arquivo `compose.yaml`.

Para consultar os logs:

```powershell
docker compose logs -f backend
docker compose logs -f prometheus
```

Para parar tudo preservando os dados:

```powershell
docker compose down
```

Use `docker compose down -v` somente quando também quiser apagar banco, workspaces
e histórico de métricas.

## Prometheus

O backend publica contadores e histogramas em `GET /metrics`. O Prometheus coleta
esse endpoint a cada 15 segundos. Em `http://localhost:9090/targets`, o target
`fullstack-agents-api` deve aparecer como `UP`.

Exemplos de consultas:

```promql
fullstack_agents_http_requests_total
rate(fullstack_agents_http_requests_total[5m])
histogram_quantile(0.95, sum by (le, path) (rate(fullstack_agents_http_request_duration_seconds_bucket[5m])))
```

## API

Abra `http://localhost:8000/docs` para a documentação interativa.

Confira `http://localhost:8000/health`. O campo `persistence` deve retornar
`mongo`.

## Testar uma run

Com a API em execução, envie o prompt pelo PowerShell:

```powershell
$body = @{
  prompt = "Quero criar um portal para clientes consultarem suas apólices."
  project_name = "portal-clientes"
} | ConvertTo-Json -Compress
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

## Criar e continuar um projeto

Para manter o mesmo código e contexto entre pedidos, use projetos. A primeira
mensagem cria o workspace; as próximas reutilizam esse mesmo workspace:

```powershell
$body = @{
  name = "calculadora-lucro"
  prompt = "Crie uma calculadora de lucro líquido."
} | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/projects" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

Guarde o `project_id` retornado. Para continuar:

```powershell
$message = @{ content = "Adicione uma explicação visual do lucro." } | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/projects/SEU_PROJECT_ID/messages" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($message))
```

Consulte o projeto, suas mensagens e suas runs:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/projects/SEU_PROJECT_ID"
Invoke-RestMethod "http://127.0.0.1:8000/projects/SEU_PROJECT_ID/messages"
Invoke-RestMethod "http://127.0.0.1:8000/projects/SEU_PROJECT_ID/runs"
```

### Repetir uma run que falhou

Erros temporários do provedor (`429` e `5xx`, incluindo `503`) são repetidos
automaticamente na mesma execução: até 3 novas tentativas, esperando 2, 4 e 8
segundos. O PO, ferramentas já usadas e workspace não são reiniciados.

Se todas as tentativas falharem, repita manualmente a run pelo mesmo endpoint de
mensagens, sem criar uma mensagem nova:

```powershell
$retry = @{ retry_run_id = "RUN_FALHADA" } | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/projects/SEU_PROJECT_ID/messages" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($retry))
```

A nova run recebe `retry_of_run_id`, reutiliza o workspace do projeto e aproveita
o backlog já produzido pelo PO. As leituras de arquivos do DEV serão refeitas,
pois a conversa com o Gemini anterior foi encerrada pelo provedor.

No fluxo atual, a run executa `PO → DEV → CODER`.

1. O **PO** transforma o pedido em requisitos e histórias. Se o pedido exigir mais
   de dez histórias de usuário, ele recusa a run com uma orientação fixa e o fluxo
   termina como `COMPLETED` sem criar workspace — recusa é escopo, não erro.
2. O **DEV** copia `code/template` para
   `DEV_WORKSPACE_ROOT\<project_name>_<id-da-run>\codigo`, inicializa um commit
   de baseline em git e **explora o código com ferramentas de leitura**
   (`list_files`, `read_file`, `grep`) antes de salvar `development-plan.json` em
   `artifacts`. Caminhos citados no plano são validados contra o workspace real.
3. O **CODER** executa o plano **escrevendo no workspace** (`write_file`,
   `delete_file`, além das ferramentas de leitura) e salva
   `implementation-report.json`.

Cada iteração de ferramenta de um agente é uma entrada `LLM_CALL` própria na
timeline, numerada em `iteration`, com as ferramentas oferecidas, as chamadas
pedidas, os resultados devolvidos e o custo daquela iteração. As escritas
efetivadas em disco são comparadas com o que o CODER declara no relatório; toda
divergência fica registrada como `CODER_REPORT_DIVERGED`.

Nenhum agente executa comandos: não há build, teste ou container no loop. Os
comandos de validação são apenas declarados, sempre copiados do bloco "Comandos
permitidos" do manifesto do template.

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
