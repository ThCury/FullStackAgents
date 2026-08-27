import { StructuredOutput } from '@/components/ui/StructuredOutput'
import { formatTokens } from '@/utils/format'
import { themeFor } from './agentTheme'
import type { AgentView } from '@/utils/runMapper'

/** Painel de detalhe abaixo do diagrama (desktop). */
export function AgentDetail({ agent }: { agent: AgentView | null }) {
  if (!agent) {
    return (
      <div className="agent-detail only-desktop">
        <p className="structured structured__text">
          Selecione um agente no diagrama acima para ver a resposta.
        </p>
      </div>
    )
  }

  const theme = themeFor(agent.status)

  return (
    <div className="agent-detail only-desktop">
      <div className="agent-detail__head">
        <span className="agent-detail__name">{agent.name}</span>
        <span
          className={`status-text${agent.status === 'running' ? ' status-text--running' : ''}`}
          style={{ color: theme.labelColor }}
        >
          {agent.statusLabel}
        </span>
        {(agent.iterations > 0 || agent.tokens !== null) && (
          <span className="agent-card__role">
            {agent.iterations} iteração(ões) · {formatTokens(agent.tokens)} tokens
          </span>
        )}
      </div>
      <div className="agent-detail__role">{agent.description}</div>
      <div className="divider" style={{ marginBottom: 14 }} />
      {agent.error && (
        <p className="field__error" style={{ marginBottom: 10 }}>
          {agent.error}
        </p>
      )}
      <div className="structured__key" style={{ marginBottom: 8 }}>
        Resposta do agente
      </div>
      <StructuredOutput
        value={agent.output}
        fallback={
          agent.status === 'pending'
            ? 'Este agente ainda não foi acionado nesta execução.'
            : 'Aguardando a resposta do modelo…'
        }
      />
    </div>
  )
}
