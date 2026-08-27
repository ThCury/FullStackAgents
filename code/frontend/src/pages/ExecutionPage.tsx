import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AgentCard } from '@/components/agents/AgentCard'
import { AgentDetail } from '@/components/agents/AgentDetail'
import { AgentPipeline } from '@/components/agents/AgentPipeline'
import { PromptComposer } from '@/components/projects/PromptComposer'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Alert, Loading } from '@/components/ui/Feedback'
import { useSession } from '@/context/SessionContext'
import { useIsDesktop } from '@/hooks/useMediaQuery'
import { useProjectExecution } from '@/hooks/useProjectExecution'
import { routes } from '@/router/routes'
import { formatDateTime, formatTokens, truncate } from '@/utils/format'
import { isRunActive, runStatusLabel } from '@/utils/runMapper'

export function ExecutionPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const isDesktop = useIsDesktop()
  const { user } = useSession()

  const { project, runs, activeRun, agents, busy, loading, error, selectRun, sendMessage } =
    useProjectExecution(projectId)

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [retryError, setRetryError] = useState<string | null>(null)

  // Ao abrir (ou trocar de run) foca no agente que está trabalhando agora.
  useEffect(() => {
    const current =
      agents.find((agent) => agent.status === 'running') ??
      [...agents].reverse().find((agent) => agent.status !== 'pending')
    setSelectedAgentId(current?.id ?? null)
  }, [activeRun?._id, activeRun?.status])

  const toggleAgent = (agentId: string) =>
    setSelectedAgentId((current) => (current === agentId ? null : agentId))

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? null
  const running = isRunActive(activeRun?.status)
  const failed = activeRun?.status === 'FAILED'

  const retry = async () => {
    if (!activeRun) return
    setRetryError(null)
    try {
      await sendMessage({
        retryRunId: activeRun._id,
        userId: user?.id ?? 'local-user',
        userName: user?.name ?? 'Usuário local',
      })
    } catch (error_) {
      setRetryError(error_ instanceof Error ? error_.message : 'Falha ao reexecutar.')
    }
  }

  if (loading && !project) {
    return (
      <div className="execution">
        <div className="execution__inner">
          <Loading label="Carregando execução…" />
        </div>
      </div>
    )
  }

  if (error && !project) {
    return (
      <div className="execution">
        <div className="execution__inner">
          <Alert>{error}</Alert>
        </div>
      </div>
    )
  }

  return (
    <div className="execution">
      <div className="execution__inner">
        <div className="execution__bar">
          <button
            type="button"
            className="execution__back"
            onClick={() => navigate(routes.home)}
            aria-label="Voltar"
          >
            ←
          </button>
          <div className="execution__prompt" title={project?.name}>
            {truncate(project?.name ?? '', 140)}
          </div>
        </div>

        <Badge tone={failed ? 'danger' : running ? 'accent' : 'muted'}>
          {runStatusLabel(activeRun)}
        </Badge>
        <h1 className="execution__headline">
          {running ? 'Orquestrando agentes' : failed ? 'A execução falhou' : 'Fluxo concluído'}
        </h1>
        <p className="execution__hint">
          {isDesktop
            ? 'Clique em um agente para ver a resposta'
            : 'Toque em um agente para ver a resposta'}
        </p>

        {isDesktop && (
          <>
            <AgentPipeline
              agents={agents}
              selectedId={selectedAgentId}
              onSelect={toggleAgent}
              active={running}
              finished={activeRun?.status === 'COMPLETED'}
            />
            <AgentDetail agent={selectedAgent} />
          </>
        )}

        {!isDesktop && (
          <div className="execution__agents">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                expanded={selectedAgentId === agent.id}
                onToggle={toggleAgent}
              />
            ))}
          </div>
        )}

        {activeRun && (
          <div className="metrics">
            <div className="metric">
              <span className="metric__label">Tokens</span>
              <span className="metric__value">
                {formatTokens(activeRun.audit?.totals?.total_tokens)}
              </span>
            </div>
            <div className="metric">
              <span className="metric__label">Iniciado</span>
              <span className="metric__value">{formatDateTime(activeRun.brasil_datetime)}</span>
            </div>
            <div className="metric">
              <span className="metric__label">Finalizado</span>
              <span className="metric__value">
                {formatDateTime(activeRun.finished_at?.brasil_datetime)}
              </span>
            </div>
            <div className="metric">
              <span className="metric__label">Execuções</span>
              <span className="metric__value">{runs.length}</span>
            </div>
          </div>
        )}

        {runs.length > 1 && (
          <div className="execution__followup">
            <span className="eyebrow">Execuções do projeto</span>
            <div className="stack">
              {runs.map((run) => (
                <button
                  key={run._id}
                  type="button"
                  className={`card card--interactive project-card${run._id === activeRun?._id ? ' nav__link--active' : ''}`}
                  onClick={() => selectRun(run._id)}
                >
                  <span className="project-card__main">
                    <span className="project-card__name">{truncate(run.input.content, 90)}</span>
                    <span className="project-card__date">
                      {formatDateTime(run.brasil_datetime)}
                    </span>
                  </span>
                  <span
                    className="status-text"
                    style={{ color: run.status === 'FAILED' ? 'var(--danger)' : 'var(--accent)' }}
                  >
                    {runStatusLabel(run)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeRun?.error && <div className="execution__followup"><Alert>{activeRun.error}</Alert></div>}
        {retryError && <div className="execution__followup"><Alert>{retryError}</Alert></div>}

        <div className="execution__followup">
          {failed && (
            <Button variant="ghost" onClick={retry} disabled={busy}>
              Reexecutar esta run
            </Button>
          )}
          <span className="eyebrow">Continuar o projeto</span>
          <PromptComposer
            onSubmit={(content) =>
              sendMessage({
                content,
                userId: user?.id ?? 'local-user',
                userName: user?.name ?? 'Usuário local',
              }).then(() => undefined)
            }
            placeholder="Ex: adicionar validação de cupom expirado..."
            submitLabel="Enviar nova instrução"
            hint="A instrução entra no mesmo workspace do projeto"
            disabled={busy}
            disabledReason="Aguarde a execução atual terminar para enviar uma nova instrução."
          />
        </div>
      </div>
    </div>
  )
}
