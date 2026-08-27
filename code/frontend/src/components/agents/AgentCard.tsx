import { StructuredOutput } from '@/components/ui/StructuredOutput'
import { formatTokens } from '@/utils/format'
import { themeFor } from './agentTheme'
import type { AgentView } from '@/utils/runMapper'

interface AgentCardProps {
  agent: AgentView
  expanded: boolean
  onToggle: (agentId: string) => void
}

/** Cartão expansível — versão mobile do diagrama (referência wireframe). */
export function AgentCard({ agent, expanded, onToggle }: AgentCardProps) {
  const theme = themeFor(agent.status)

  return (
    <div className="agent-card" style={{ borderColor: theme.borderColor }}>
      <button
        type="button"
        className="agent-card__header"
        onClick={() => onToggle(agent.id)}
        aria-expanded={expanded}
      >
        <span className="agent-card__avatar" style={{ borderColor: theme.borderColor, color: theme.iconColor }}>
          {agent.initial}
        </span>
        <span className="agent-card__meta">
          <span className="agent-card__name">{agent.name}</span>
          <span className="agent-card__role">{agent.description}</span>
        </span>
        <span
          className={`status-text${agent.status === 'running' ? ' status-text--running' : ''}`}
          style={{ color: theme.labelColor, paddingTop: 3 }}
        >
          {agent.statusLabel}
        </span>
      </button>

      {expanded && (
        <div className="agent-card__body">
          <div className="divider" />
          {agent.error && <p className="field__error">{agent.error}</p>}
          <span className="structured__key">Resposta do agente</span>
          <StructuredOutput
            value={agent.output}
            fallback={
              agent.status === 'pending'
                ? 'Este agente ainda não foi acionado nesta execução.'
                : 'Aguardando a resposta do modelo…'
            }
          />
          {(agent.iterations > 0 || agent.tokens !== null) && (
            <span className="agent-card__role">
              {agent.iterations} iteração(ões) · {formatTokens(agent.tokens)} tokens
            </span>
          )}
        </div>
      )}
    </div>
  )
}
