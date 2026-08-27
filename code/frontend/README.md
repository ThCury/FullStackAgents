# Full Stack Agents — Frontend

SPA em React + TypeScript (Vite) que consome a API FastAPI de `code/backend`.
Um único código responsivo cobre as duas referências de design em `reference/`:
topbar + diagrama SVG no desktop, tab bar + cartões expansíveis no mobile
(breakpoint em 768px).

## Rodando

```bash
npm install
npm run dev
```

A API é lida de `VITE_API_BASE_URL` (`.env`, padrão `http://localhost:8000`).
O backend já libera CORS para `http://localhost:5173`
(`BackendConfig.cors_allow_origins`).

Scripts: `npm run dev`, `npm run build`, `npm run preview`, `npm run lint` (tsc).

## Estrutura

```
src/
  components/
    agents/     AgentPipeline (desktop), AgentCard (mobile), AgentDetail, agentTheme
    layout/     AppShell, TopBar, TabBar, Brand
    projects/   ProjectCard, PromptComposer
    ui/         Button, Field, Badge, Feedback, StructuredOutput
  config/       env, agents (fluxo PO → DEV → CODER), navigation
  context/      SessionContext (identificação local)
  hooks/        useAsync (fetch + polling), useProjectExecution, useMediaQuery
  pages/        Login, Home, Execution, History, Profile
  router/       AppRouter, ProtectedRoute, routes
  services/     httpClient, projectsApi, runsApi
  styles/       tokens.css, components.css, pages.css, global.css
  types/        api.ts (contratos do backend)
  utils/        runMapper (auditoria → estado dos agentes), format
```

## Integração com o backend

| Tela | Endpoints |
| --- | --- |
| Home | `GET /projects`, `POST /projects` |
| Histórico | `GET /projects` |
| Execução | `GET /projects/{id}`, `GET /projects/{id}/runs`, `POST /projects/{id}/messages` |

`src/services/runsApi.ts` também cobre `GET /runs`, `GET /runs/{id}` (`resume`/`full`)
e `GET /runs/{id}/result` para telas futuras.

O backend não expõe um "status do agente": `src/utils/runMapper.ts` deriva
`pending | running | done | failed` de `audit.timeline` (chamadas `LLM_CALL` por
`agent.id`) e pega a entrega de cada agente do artefato correspondente —
`output` da run para o PO, `development_plan` para o Developer e
`implementation_report` para o Coder. Enquanto a run está `PENDING`/`RUNNING`,
a página de execução refaz a consulta a cada `VITE_POLL_INTERVAL_MS`.

## Login

O backend ainda não tem autenticação — só recebe `requested_by_id` e
`requested_by_name` em cada comando. A tela de login apenas guarda essa
identificação no `localStorage`; nenhuma senha é pedida ou enviada. Ao ligar
uma autenticação real, trocar `src/context/SessionContext.tsx` e adicionar o
header no `src/services/httpClient.ts`.

## Agentes exibidos

As referências desenham seis agentes (PO, Arquiteto, Dev, Coder, QA, DevOps).
O grafo implementado hoje tem três — PO → DEV → CODER (`pipeline/graph.py`) —
e são esses os que aparecem. Para incluir novos, basta adicionar a entrada em
`src/config/agents.ts` com o `id` que o backend usa na auditoria.
