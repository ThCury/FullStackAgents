import { AGENTS, type AgentDefinition } from '@/config/agents'
import type { RunFull, TimelineLLMCall } from '@/types/api'

export type AgentStatus = 'pending' | 'running' | 'done' | 'failed'

export interface AgentView extends AgentDefinition {
  status: AgentStatus
  statusLabel: string
  /** Saída final do agente: artefato estruturado ou texto da última chamada. */
  output: unknown
  iterations: number
  tokens: number | null
  events: string[]
  error: string | null
}

const STATUS_LABEL: Record<AgentStatus, string> = {
  pending: 'Espera',
  running: 'Rodando',
  done: 'OK',
  failed: 'Falhou',
}

function isLLMCall(item: unknown): item is TimelineLLMCall {
  return !!item && typeof item === 'object' && (item as { type?: string }).type === 'LLM_CALL'
}

function callsOf(run: RunFull, agentId: string): TimelineLLMCall[] {
  return (run.audit?.timeline ?? []).filter(
    (item): item is TimelineLLMCall => isLLMCall(item) && item.agent?.id === agentId,
  )
}

function eventsOf(run: RunFull, agentId: string): string[] {
  return (run.audit?.timeline ?? [])
    .filter((item) => {
      if (!item || typeof item !== 'object') return false
      const record = item as { type?: string; to?: { id?: string } }
      return record.type === 'FLOW_EVENT' && record.to?.id === agentId
    })
    .map((item) => String((item as { summary?: string }).summary ?? ''))
    .filter(Boolean)
}

function artifactContent(run: RunFull, artifactType: string | undefined): unknown {
  if (!artifactType) return null
  const artifact = [...(run.artifacts ?? [])].reverse().find((item) => item.type === artifactType)
  return artifact?.content?.content ?? null
}

function sumTokens(calls: TimelineLLMCall[]): number | null {
  const values = calls
    .map((call) => call.usage?.total_tokens)
    .filter((value): value is number => typeof value === 'number')
  return values.length ? values.reduce((total, value) => total + value, 0) : null
}

/**
 * Deriva o estado de cada agente a partir da run completa. O backend não expõe
 * um campo "status do agente": ele é inferido da timeline de auditoria.
 */
export function mapAgents(run: RunFull | null): AgentView[] {
  return AGENTS.map((definition) => {
    if (!run) {
      return {
        ...definition,
        status: 'pending' as const,
        statusLabel: STATUS_LABEL.pending,
        output: null,
        iterations: 0,
        tokens: null,
        events: [],
        error: null,
      }
    }

    const calls = callsOf(run, definition.id)
    const lastCall = calls.at(-1) ?? null
    const callError = calls.map((call) => call.error).filter(Boolean).at(-1) ?? null

    let status: AgentStatus = 'pending'
    if (calls.length > 0) {
      const stillStreaming = calls.some((call) => call.status === 'STREAMING')
      if (callError) status = 'failed'
      else if (stillStreaming && run.status === 'RUNNING') status = 'running'
      else status = 'done'
    }
    // Sem chamadas o agente segue `pending`, mesmo numa run que falhou antes
    // de chegar nele — quem carrega o erro é o agente que estava executando.

    // A entrega do PO é o backlog: output da run, snapshot ou backlog herdado
    // de uma reexecução (nesse caso o PO não roda de novo).
    const backlog = run.output ?? run.backlog_snapshot ?? run.resume_backlog ?? null
    const structured =
      definition.id === 'po' ? backlog : artifactContent(run, definition.artifactType)

    // PO sem chamadas mas com backlog herdado: entrega reaproveitada, não espera.
    const reused = definition.id === 'po' && calls.length === 0 && backlog !== null
    if (reused) status = 'done'

    return {
      ...definition,
      status,
      statusLabel: reused ? 'Reusado' : STATUS_LABEL[status],
      output: structured ?? (lastCall?.response?.content || null),
      iterations: lastCall?.iteration ?? calls.length,
      tokens: sumTokens(calls),
      events: eventsOf(run, definition.id),
      // O erro da run aparece uma vez, no topo da página; aqui só o da chamada.
      error: callError,
    }
  })
}

export function isRunActive(status: string | undefined): boolean {
  return status === 'PENDING' || status === 'RUNNING'
}

export function runStatusLabel(run: { status: string } | null): string {
  if (!run) return 'Aguardando'
  switch (run.status) {
    case 'PENDING':
      return 'Na fila'
    case 'RUNNING':
      return 'Executando'
    case 'COMPLETED':
      return 'Concluído'
    case 'FAILED':
      return 'Falhou'
    default:
      return run.status
  }
}
