# Plano do backend inicial — PO com LangGraph e auditoria

## 1. Escopo desta primeira implementação

Construir somente o backend que recebe um prompt, chama um agente Product Owner e
retorna requisitos e histórias de usuário. Não haverá DEV, QA, geração de código,
workspace, Git ou sandbox nesta fase.

O fluxo inicial é curto e propositalmente simples:

```mermaid
flowchart LR
    U[POST /runs] --> A[Registrar run e USER_PROMPT]
    A --> G[LangGraph: PO]
    G --> L[Gateway LLM auditável]
    L --> M[(MongoDB)]
    G --> V[Validar saída estruturada]
    V --> R[Salvar PRODUCT_BACKLOG]
    R --> C[Run concluído]
```

## 2. Contrato do PO

**Entrada:** prompt do usuário e system prompt versionado do PO.

**Saída estruturada:**

```json
{
  "summary": "Resumo do entendimento",
  "requirements": [
    {"id": "RF-001", "description": "...", "priority": "must"}
  ],
  "user_stories": [
    {
      "id": "US-001",
      "title": "...",
      "as_a": "...",
      "i_want": "...",
      "so_that": "...",
      "acceptance_criteria": ["..."],
      "priority": "must"
    }
  ],
  "assumptions": ["..."],
  "open_questions": ["..."]
}
```

O PO não escreve arquivos, não escolhe stack, não chama ferramentas e não aprova
o próprio resultado. A validação Pydantic rejeita saída sem requisitos ou histórias
e registra a tentativa no fluxo.

## 3. Estrutura de pastas proposta

```text
code/backend/
├── pyproject.toml
├── .env.example
├── src/
│   └── fullstack_agents/
│       ├── main.py                    # composição FastAPI
│       ├── config.py                  # settings e variáveis de ambiente
│       ├── domain/
│       │   ├── entities/              # Run agregado e itens da audit.timeline
│       │   ├── enums.py               # estados, papéis e tipos de evento
│       │   ├── schemas/               # ProductBacklog e contratos do PO
│       │   └── ports/                 # Protocols de LLM, auditoria e repositórios
│       ├── application/
│       │   ├── use_cases/
│       │   │   ├── start_po_run.py    # cria e executa um run
│       │   │   ├── get_run.py
│       │   │   └── get_audit_trail.py
│       │   └── services/              # AuditRecorder e CostCalculator
│       ├── agents/
│       │   └── product_owner/
│       │       ├── agent.py           # adapta contrato do PO ao gateway
│       │       └── system_prompt.md   # versionado junto ao código
│       ├── pipeline/
│       │   ├── state.py               # estado mínimo do LangGraph
│       │   ├── graph.py               # grafo de um nó PO
│       │   └── nodes.py               # nó de planejamento
│       ├── infrastructure/
│       │   ├── llm/                   # adaptador real, fake e gateway auditável
│       │   ├── mongo/                 # cliente, coleção runs, índices e repositório
│       │   └── clock.py               # UTC + America/Sao_Paulo em um único ponto
│       └── interfaces/
│           └── http/
│               ├── router_runs.py
│               ├── router_audit.py
│               └── dependencies.py
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

`domain/` não importa FastAPI, LangGraph, PyMongo/Motor nem SDK de LLM. LangGraph
fica em `pipeline/`; MongoDB e o provedor são detalhes em `infrastructure/`.

## 4. Endpoints iniciais

| Método | Rota | Resultado |
|---|---|---|
| `POST` | `/runs` | Recebe `prompt`, cria run e inicia o grafo. Devolve `202` e `run_id`. |
| `GET` | `/runs/{run_id}` | Estado, resumo e totais de token/custo. |
| `GET` | `/runs/{run_id}/result` | Requisitos e histórias aceitos. |
| `GET` | `/runs/{run_id}/audit` | Mensagens, chamadas LLM e eventos do fluxo em ordem. |
| `GET` | `/health` | Saúde da API, MongoDB e configuração não sensível. |

O primeiro `POST` pode executar o grafo em tarefa assíncrona local. Uma fila só
deve ser avaliada após o fluxo e a auditoria estarem estáveis.

## 5. Plano de implementação

| Etapa | Entrega | Critério de pronto |
|---|---|---|
| 1. Fundação | Projeto Python, configuração, FastAPI, Docker Compose com MongoDB e health check. | API sobe e valida conexão sem expor segredos. |
| 2. Modelo Mongo | Coleção `runs`, validador e índices do documento agregado. | Inserções inválidas são recusadas; um `findOne` por `run_id` traz o histórico. |
| 3. Auditoria | `AuditRecorder`, relógio UTC/Brasília e `CostCalculator`. | Um fluxo fake acrescenta itens de timeline para entrada, chamada e eventos. |
| 4. PO fake | Contratos Pydantic, agente PO e LangGraph de um nó usando LLM fake. | `POST /runs` produz backlog determinístico e auditável. |
| 5. LLM real | Adaptador do provedor configurado por ambiente e gateway auditável. | Tokens, latência, modelo, esforço e custo são persistidos. |
| 6. API de consulta | Endpoints de status, resultado e auditoria paginada. | Usuário consulta um run sem acessar Mongo diretamente. |
| 7. Qualidade | Testes, reconciliação de totais e documentação operacional. | Testes unitários, integração Mongo e e2e passam. |

## 6. Testes obrigatórios antes de adicionar DEV/QA

- o mesmo prompt cria `USER_PROMPT`, `SYSTEM_PROMPT`, `LLM_PROMPT`,
  `LLM_RESPONSE`, `AGENT_RESULT` e eventos esperados;
- `brasil_datetime` existe e representa o mesmo instante de `timestamp`;
- erro/timeout do provedor produz `LLM_CALL_FAILED`, custo/tokens conhecidos e run
  em estado terminal apropriado;
- retry não duplica chamada nem custo quando a chave de idempotência já concluiu;
- soma das chamadas `LLM_CALL` na timeline coincide com `audit.totals`;
- saída inválida do PO não gera `PRODUCT_BACKLOG` aceito;
- o endpoint de auditoria retorna conteúdo, remetente, destinatário, modelo,
  agente, system prompt, esforço, tokens, custo, tentativa e latência.

## 7. Próximo incremento depois desta fase

Somente quando este caminho estiver testado: adicionar um nó DEV, contratos de
handoff e workspace isolado. QA, execução de código e suporte a projetos existentes
entram em incrementos posteriores, reaproveitando as mesmas coleções de auditoria.
