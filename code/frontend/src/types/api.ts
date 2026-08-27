/** Contratos da API FastAPI (code/backend/routes). */

export type RunExecutionStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
export type RunPublicStatus = 'PENDING' | 'SUCCESS' | 'FAILED'

export interface Actor {
  type: string
  id: string
  display_name: string | null
}

export interface AuditTime {
  timestamp: string
  brasil_datetime: string
}

export interface CreateProjectPayload {
  name: string
  prompt: string
  requested_by_id: string
  requested_by_name: string | null
}

export interface CreateProjectResponse {
  project_id: string
  run_id: string
  status: RunExecutionStatus
  brasil_datetime: string
}

export interface CreateMessagePayload {
  content?: string
  retry_run_id?: string
  requested_by_id: string
  requested_by_name: string | null
}

export interface CreateMessageResponse {
  project_id: string
  run_id: string
  retry_of_run_id: string | null
  status: RunExecutionStatus
  brasil_datetime: string
}

export interface ProjectListItem {
  project_id: string
  name: string
  status: string
  last_run_id: string | null
  brasil_datetime: string
}

export interface ProjectContext {
  summary: string
  decisions: unknown[]
  backlog: Record<string, unknown> | null
  last_run_id: string | null
}

export interface ProjectMessage {
  id: string
  role: string
  author: Actor
  content: string
  timestamp: string
  brasil_datetime: string
}

export interface Project {
  _id: string
  name: string
  status: string
  requested_by: Actor
  workspace: Record<string, string> | null
  context: ProjectContext
  messages: ProjectMessage[]
  version: number
  timestamp: string
  brasil_datetime: string
}

export interface RunListItem {
  run_id: string
  project_id: string | null
  status: RunPublicStatus
  prompt_preview: string
  requested_by: { id: string; display_name: string | null }
  brasil_datetime: string
  finished_brasil_datetime: string | null
}

/**
 * Projeção devolvida por `GET /projects/{id}/runs` — o repositório Mongo corta
 * auditoria e artefatos; o documento completo vem de `GET /runs/{id}?dataset=full`.
 */
export interface RunSummary {
  _id: string
  flow: string
  project_id: string | null
  status: RunExecutionStatus
  requested_by: Actor
  input: { content: string }
  brasil_datetime: string
  finished_at: { brasil_datetime: string } | null
}

export interface RunResume {
  run_id: string
  flow: string
  status: RunPublicStatus
  execution_status: RunExecutionStatus
  requested_by: Actor
  prompt_sent: string
  response_received: Record<string, unknown> | null
  tokens_spent: {
    input: number | null
    output: number | null
    cached: number | null
    total: number | null
  }
  time_spent: {
    started_at: string
    finished_at: string | null
    duration_ms: number | null
  }
  llm: {
    agent: { id: string; role: string; version: string }
    provider: string
    model: string
    system_prompt: string
    effort: string | null
  } | null
  error: string | null
}

export interface TimelineLLMCall {
  sequence: number
  type: 'LLM_CALL'
  call_id: string
  iteration: number
  retry_attempt: number
  agent: { id: string; role: string; version: string }
  request: Record<string, unknown>
  response: { content: string; [key: string]: unknown }
  tool_calls: unknown[]
  tool_results: unknown[]
  usage: Record<string, number | null>
  status: string
  error: string | null
  latency_ms?: number
  brasil_datetime: string
}

export interface TimelineFlowEvent {
  sequence: number
  type: 'FLOW_EVENT'
  event: string
  approved: boolean | null
  summary: string
  to?: { type: string; id?: string; role?: string }
  brasil_datetime: string
}

export type TimelineItem = TimelineLLMCall | TimelineFlowEvent | { type: string; [key: string]: unknown }

export interface RunArtifact {
  id: string
  type: string
  content: Record<string, unknown>
  brasil_datetime: string
}

export interface RunFull {
  _id: string
  flow: string
  project_id: string | null
  mode: string
  retry_of_run_id: string | null
  status: RunExecutionStatus
  requested_by: Actor
  input: { content: string; project_name: string; brasil_datetime: string }
  audit: {
    next_sequence: number
    timeline: TimelineItem[]
    totals: {
      input_tokens: number | null
      output_tokens: number | null
      cached_tokens: number | null
      total_tokens: number | null
      [key: string]: unknown
    }
  }
  output: Record<string, unknown> | null
  /** Backlog reaproveitado numa reexecução — o PO não roda de novo. */
  resume_backlog: Record<string, unknown> | null
  backlog_snapshot?: Record<string, unknown> | null
  artifacts: RunArtifact[]
  brasil_datetime: string
  finished_at: AuditTime | null
  error: string | null
}
