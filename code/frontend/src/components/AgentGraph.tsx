import { useEffect, useMemo, useState } from 'react'
import type { AgentMessage, AgentRole } from '../api/client'
import { Deliverables, type DeliverableTab } from './Deliverables'
import { Timeline } from './Timeline'

interface NodeDefinition {
  role: AgentRole
  label: string
  short: string
  description: string
  tabs: DeliverableTab[]
}

const NODES: NodeDefinition[] = [
  {
    role: 'briefing_analyst',
    label: 'Briefing Analyst',
    short: 'Briefing',
    description: 'Normaliza o problema, restrições e vocabulário antes do planejamento.',
    tabs: [],
  },
  {
    role: 'product_owner',
    label: 'PO Agent',
    short: 'Backlog',
    description: 'Interpreta o briefing e cria stories priorizadas com critérios de aceite.',
    tabs: ['backlog'],
  },
  {
    role: 'developer',
    label: 'Dev Agent',
    short: 'Código',
    description: 'Implementa cada story e registra as decisões técnicas tomadas.',
    tabs: ['adrs', 'artifacts'],
  },
  {
    role: 'qa',
    label: 'QA Agent',
    short: 'Validação',
    description: 'Executa os casos de teste e devolve reprovações para correção.',
    tabs: ['qa'],
  },
  {
    role: 'orchestrator',
    label: 'Orquestrador',
    short: 'Integração',
    description: 'Controla o fluxo, os handoffs e a integração da entrega final.',
    tabs: ['backlog', 'adrs', 'qa', 'artifacts'],
  },
]

interface Props {
  runId: string
  messages: AgentMessage[]
  activeNode: string | null
}

export function AgentGraph({ runId, messages, activeNode }: Props) {
  const [selected, setSelected] = useState<NodeDefinition | null>(null)

  useEffect(() => {
    if (!selected) return

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setSelected(null)
    }

    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [selected])

  const activityByRole = useMemo(
    () =>
      Object.fromEntries(
        NODES.map((node) => [
          node.role,
          messages.filter(
            (message) => message.from_agent === node.role || message.to_agent === node.role,
          ).length,
        ]),
      ) as Record<AgentRole, number>,
    [messages],
  )

  const selectedMessages = selected
    ? messages.filter(
        (message) =>
          message.from_agent === selected.role || message.to_agent === selected.role,
      )
    : []

  return (
    <section className="graph-panel" aria-label="Pipeline do squad">
      <header className="graph-panel__header">
        <div>
          <p className="eyebrow">Pipeline do squad</p>
          <h2>Acompanhe sem abrir todos os detalhes</h2>
        </div>
        <p className="muted">Clique em um nó para ver comunicação e entregáveis.</p>
      </header>

      <div className="agent-graph">
        {NODES.map((node, index) => {
          const count = activityByRole[node.role] ?? 0
          const isActive = activeNode === node.role
          const state = isActive ? 'active' : count > 0 ? 'done' : 'waiting'

          return (
            <div className="agent-graph__step" key={node.role}>
              <button
                type="button"
                className={`agent-node agent-node--${node.role} agent-node--${state}`}
                onClick={() => setSelected(node)}
                aria-label={`Abrir detalhes de ${node.label}`}
              >
                <span className="agent-node__state" aria-hidden />
                <span className="agent-node__short">{node.short}</span>
                <strong>{node.label}</strong>
                <span className="agent-node__meta">
                  {isActive ? 'trabalhando…' : count > 0 ? `${count} eventos` : 'aguardando'}
                </span>
              </button>
              {index < NODES.length - 1 && (
                <span className="agent-graph__arrow" aria-hidden>
                  →
                </span>
              )}
            </div>
          )
        })}
      </div>

      {selected && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelected(null)
          }}
        >
          <section
            className={`node-modal node-modal--${selected.role}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="node-modal-title"
          >
            <header className="node-modal__header">
              <div>
                <p className="eyebrow">{selected.short}</p>
                <h2 id="node-modal-title">{selected.label}</h2>
                <p>{selected.description}</p>
              </div>
              <button type="button" className="node-modal__close" onClick={() => setSelected(null)}>
                Fechar
              </button>
            </header>

            <div className="node-modal__body">
              {selected.tabs.length > 0 && (
                <Deliverables
                  key={selected.role}
                  runId={runId}
                  refreshKey={messages.length}
                  defaultTab={selected.tabs[0]}
                  visibleTabs={selected.tabs}
                />
              )}

              <Timeline
                runId={runId}
                messages={selectedMessages}
                activeNode={activeNode === selected.role ? activeNode : null}
              />
            </div>
          </section>
        </div>
      )}
    </section>
  )
}
