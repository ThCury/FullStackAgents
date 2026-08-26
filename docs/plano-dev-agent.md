# Plano — Agente DEV e projetos gerados

## 1. Objetivo

Evoluir o MVP atual (PO auditável) com um agente DEV capaz de transformar o
backlog do PO em um projeto web novo ou em alterações isoladas de um projeto
existente. Esta fase não implementa o DEV: define o contrato, o workspace, o
projeto de referência e a execução dos projetos gerados.

## 2. Decisões do plano

- O DEV não cria uma aplicação do zero por padrão. Para `new_project`, ele copia
  um projeto de referência versionado e modifica apenas o necessário.
- O diretório-base do workspace é local à máquina e fica no `.env`, pois varia
  por computador e define um limite de segurança. Modelos, prompts de sistema e
  regras continuam versionados no código.
- Cada run possui uma pasta própria; o DEV só pode escrever nela.
- O código gerado nunca roda dentro do processo da API. Compilação, testes e
  execução ocorrem em containers do projeto gerado.
- Todo projeto gerado oferece a mesma interface operacional: Docker Compose.

## 3. Configuração local do workspace

Quando o DEV for implementado, o arquivo `code/backend/.env` terá a chave abaixo,
além das chaves de LLM:

```dotenv
DEV_WORKSPACE_ROOT=C:\FullStackAgents\workspaces
```

O valor deve ser um caminho absoluto dedicado ao produto; não deve apontar para a
raiz do usuário, para a pasta do repositório do orquestrador, nem para uma pasta
com projetos pessoais. A aplicação validará que o caminho existe ou o criará uma
única vez na inicialização. Antes de criar, copiar, executar ou apagar algo, ela
resolve o caminho final e confirma que ele continua abaixo de `DEV_WORKSPACE_ROOT`.

Estrutura para um novo projeto:

```text
DEV_WORKSPACE_ROOT/
└── login-todo_8f0ec8f2/
    ├── codigo/                 # único diretório alterável pelo DEV
    ├── manifest.json           # origem, run_id, template e hashes
    ├── artifacts/              # relatórios de build, teste e QA
    └── logs/                   # saída sanitizada de comandos
```

O sufixo é o UUID da run. O nome é normalizado (`a-z`, `0-9` e hífen), evitando
caminhos especiais. O `manifest.json` relaciona workspace, `run_id`, versão do
template, comandos executados e hashes dos artefatos; a run no Mongo guarda só os
metadados e referências a esses arquivos.

## 4. Projeto de referência: Login + Todo

O template será um projeto real, mantido e testado no repositório, por exemplo em
`code/template/`. Ele é o ponto de partida para todo `new_project` e deve
ter versão semântica (`template_version`, por exemplo `1.0.0`).

Escopo funcional mínimo:

- cadastro, login, logout e sessão autenticada;
- página privada após login;
- CRUD de tarefas: criar, listar, editar, concluir e excluir;
- uma tarefa pertence somente ao usuário autenticado;
- validação de campos, estados de carregamento e mensagens de erro;
- testes automatizados do fluxo de autenticação e CRUD.

Contrato obrigatório do template:

```text
code/template/
├── compose.yaml
├── README.md
├── .env.example
├── Makefile ou scripts/        # atalhos equivalentes para Windows
├── frontend/
├── backend/
└── docs/
    └── agent-manifest.md       # tecnologias, comandos, portas e arquivos-chave
```

O `agent-manifest.md` é deliberadamente curto e será passado ao DEV antes do
código. Ele informa comandos permitidos, arquitetura, convenções, onde ficam as
rotas e testes, e quais variáveis de ambiente são necessárias. Assim o agente não
precisa redescobrir o projeto inteiro a cada execução.

### Stack do template — decisão pendente

Antes da implementação, devemos aprovar uma stack única para `login-todo`.
Stack aprovada: frontend React + TypeScript, backend FastAPI + Python em MVC e
PostgreSQL. Isso mantém um projeto realmente fullstack, reaproveita Python e usa
três containers (`frontend`, `backend` e `postgres`) via Docker Compose. O DEV não
escolhe a stack por conta própria.

## 5. Fluxo do DEV para projeto novo

```text
PO aprovado
  -> orquestrador cria workspace e manifest
  -> copia code/template para codigo/
  -> DEV recebe backlog + manifest do template + arquivos relevantes
  -> DEV planeja alteração por história
  -> DEV escreve somente em codigo/
  -> executor isolado compila e testa
  -> QA recebe critérios, diff e evidências
  -> Mongo recebe referências, status e auditoria
```

Passos detalhados:

1. O orquestrador recebe o backlog aprovado e cria o workspace com UUID.
2. Um `WorkspaceManager` copia o template para `codigo/`, sem chamar a LLM.
3. Um `ProjectInspector` lê `agent-manifest.md`, árvore limitada e somente os
   arquivos relacionados à história atual.
4. O DEV recebe o contexto mínimo: história, critérios de aceite, diagnóstico e
   arquivos selecionados. Ele retorna plano, arquivos alterados e decisões.
5. Um `CommandExecutor` em container executa lint, testes e build definidos no
   manifest. Saídas são mascaradas e salvas em `artifacts/`.
6. O QA recebe os critérios, diff e evidências de build/teste. Uma reprovação abre
   nova tentativa do DEV, sem apagar os eventos anteriores.

Para reduzir tokens, o contexto nunca inclui o projeto inteiro: primeiro vai o
manifest; depois uma árvore limitada; por último, apenas arquivos sob demanda. O
DEV usa diff e resultados anteriores na tentativa seguinte, não reexplica o
template a cada chamada.

## 6. Compilar e rodar facilmente

Todo template e todo projeto derivado deve manter estes comandos no diretório
`codigo/`:

```powershell
docker compose up --build
```

Esse é o comando único para compilar imagens e iniciar a aplicação. Para rodar em
segundo plano:

```powershell
docker compose up --build -d
docker compose ps
```

O template também deverá expor comandos verificáveis pelo executor, por exemplo:

```powershell
docker compose run --rm backend python -m pytest
docker compose run --rm frontend test
docker compose down
```

Os nomes definitivos dos serviços dependem da stack aprovada, mas o contrato é:

- `compose.yaml` não depende do Docker Compose do orquestrador;
- portas, URLs e variáveis estão documentadas no `README.md` do projeto gerado;
- dados locais usam volumes nomeados pelo projeto, não o Mongo do orquestrador;
- cada comando possui timeout, código de saída e log no `manifest.json`;
- o executor não monta o `.env` do orquestrador nem suas credenciais no container
  de código gerado.

## 7. Componentes a implementar depois do plano

| Componente | Responsabilidade | Porta necessária |
|---|---|---|
| `WorkspaceManager` | validar raiz, criar workspace, copiar template e listar arquivos | `WorkspaceRepository` |
| `ProjectInspector` | criar contexto mínimo e seguro do projeto | `ProjectReader` |
| `DeveloperAgent` | planejar e produzir alterações por história | `StreamingLLM` |
| `CommandExecutor` | executar build, lint e testes de forma isolada | `ProjectCommandRunner` |
| `ArtifactRecorder` | registrar hashes, logs, diff e referências no Mongo | `ArtifactRepository` |
| Nó `dev` do LangGraph | orquestrar diagnóstico, alteração e evidências | contratos PO/DEV/QA |

Aplicação de SOLID:

- o domínio conhece `Workspace`, `BuildResult` e portas, não Docker ou sistema de
  arquivos;
- o adaptador local implementa paths; o adaptador Docker implementa comandos;
- o agente depende de interfaces de leitura, escrita e execução, permitindo fakes
  em testes;
- cada componente tem uma única responsabilidade auditável.

## 8. Fases de implementação

| Fase | Entrega | Critério de aceite |
|---|---|---|
| 0 | ADR da stack e template `login-todo` funcional | template sobe e seus testes passam manualmente |
| 1 | configuração `DEV_WORKSPACE_ROOT` e `WorkspaceManager` | cria workspace seguro e copia o template |
| 2 | modelos, portas e eventos de artefato | cada arquivo e comando é associado a uma run |
| 3 | executor Docker isolado | build/teste têm timeout, logs e código de saída |
| 4 | `DeveloperAgent` e nó DEV | altera uma história do template e registra diff |
| 5 | integração DEV → QA → DEV | reprovação gera nova tentativa auditável |
| 6 | rotas de consulta de artefatos e instruções de execução | usuário encontra workspace, resultado e comando de execução |

## 9. Fora desta fase

- acesso irrestrito do agente ao computador;
- deploy automático, push, merge ou exclusão automática de workspaces;
- geração de uma stack nova a cada prompt;
- suporte simultâneo a múltiplas stacks de template.
