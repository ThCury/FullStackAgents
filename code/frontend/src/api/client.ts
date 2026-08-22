/**
 * Cliente da API do Squad.
 *
 * Camada fina e única: nenhum componente monta URL ou chama `fetch` direto.
 * É o equivalente das *ports* do backend — trocar o transporte não toca a UI.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type AgentRole =
  | 'briefing_analyst'
  | 'product_owner'
  | 'developer'
  | 'qa'
  | 'orchestrator'
  | 'human'

export type MessageKind = 'handoff' | 'delivery' | 'rejection' | 'question' | 'decision'

export type RunStatus =
  | 'pending'
  | 'running'
  | 'awaiting_human'
  | 'completed'
  | 'failed'

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_write_tokens: number
}

export interface AgentMessage {
  id: string
  run_id: string
  seq: number
  from_agent: AgentRole
  to_agent: AgentRole
  kind: MessageKind
  ref: string | null
  summary: string
  payload: Record<string, unknown>
  rationale: string
  usage: TokenUsage
  llm_call_ref: string | null
  created_at: string | null
}

export interface Run {
  id: string
  status: RunStatus
  raw_briefing: string
  workspace_path: string | null
  failure_reason: string | null
  awaiting_reason: string | null
  created_at: string | null
}

export interface LlmCall {
  id: string
  agent: AgentRole
  model: string
  system_prompt: string
  user_prompt: string
  raw_response: string
  usage: TokenUsage
  latency_ms: number
  prompt_hash: string
  effort: string
}

export interface Metrics {
  budget: {
    total_spent: number
    total_cost_usd: number
    spent_by_agent: Record<string, number>
    extensions_approved: number
  }
  calls_total: number
  cache_hits: number
  cache_hit_rate: number
  latency_ms_avg: number
}

export interface Deliverables {
  backlog: Story[]
  adrs: Adr[]
  test_reports: TestReport[]
  artifacts: Artifact[]
  message_count: number
}

export interface AcceptanceCriterion {
  id: string
  given: string
  when: string
  then: string
}

export interface Story {
  id: string
  title: string
  narrative: string
  priority: 'must' | 'should' | 'could' | 'wont'
  scenario_tag: string | null
  acceptance_criteria: AcceptanceCriterion[]
  rationale: string
  status: string
}

export interface Adr {
  id: string
  story_ref: string
  title: string
  context: string
  decision: string
  alternatives_considered: string[]
  rationale: string
  consequences: string
}

export interface TestCase {
  id: string
  criterion_ref: string
  title: string
  expected: string
  actual: string
  outcome: 'passed' | 'failed' | 'skipped'
  evidence: { kind: string; path_or_inline: string }[]
}

export interface TestReport {
  id: string
  story_ref: string
  attempt: number
  verdict: 'approved' | 'rejected'
  cases: TestCase[]
  summary: string
  rejection_reason: string | null
  required_changes: string[]
}

export interface Artifact {
  id: string
  story_ref: string
  attempt: number
  files: { path: string; content: string; kind: string }[]
  how_to_verify: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    // A mensagem do backend é útil (contrato violado, cenário faltando).
    // Engolir isso e mostrar "erro" genérico esconde justamente o diagnóstico.
    const detail = await response.text()
    throw new Error(`${response.status} ${path}: ${detail}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  startRun: (briefing: string) =>
    request<Run>('/runs', { method: 'POST', body: JSON.stringify({ briefing }) }),

  listRuns: () => request<Run[]>('/runs'),

  getRun: (runId: string) => request<Run>(`/runs/${runId}`),

  /** `sinceSeq` busca só o delta — usado ao reconectar o SSE. */
  timeline: (runId: string, sinceSeq = -1) =>
    request<AgentMessage[]>(`/runs/${runId}/timeline?since_seq=${sinceSeq}`),

  llmCall: (runId: string, callId: string) =>
    request<LlmCall>(`/runs/${runId}/calls/${callId}`),

  deliverables: (runId: string) => request<Deliverables>(`/runs/${runId}/deliverables`),

  metrics: (runId: string) => request<Metrics>(`/runs/${runId}/metrics`),

  resume: (runId: string, resolution: 'retry' | 'skip' | 'finish') =>
    request<Run>(`/runs/${runId}/resume`, {
      method: 'POST',
      body: JSON.stringify({ resolution }),
    }),

  streamUrl: (runId: string) => `${BASE}/runs/${runId}/stream`,
}
