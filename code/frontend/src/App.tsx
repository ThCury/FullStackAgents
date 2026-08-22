/**
 * Squad Console.
 *
 * Duas colunas: a comunicação do squad à esquerda (o que decide a nota) e os
 * entregáveis + métricas à direita.
 *
 * O que ainda falta (issues abertas para o time, ver README):
 *   - Grafo ao vivo com React Flow, nós acendendo por nó executado
 *   - Diff do estado antes/depois de cada nó no Inspector
 *   - Preview embutido do app Rivexx gerado
 */

import { useEffect, useState } from 'react'
import { api, type Run } from './api/client'
import { Deliverables } from './components/Deliverables'
import { Timeline } from './components/Timeline'
import { useSquadRun } from './hooks/useSquadRun'
import './styles/app.css'

const BRIEFING_PLACEHOLDER = `Cole aqui o briefing do cliente.

Ex.: Rivexx Componentes — indústria de componentes plásticos de alta precisão,
2 plantas, 480 colaboradores, operação em 3 turnos. Toda não conformidade
detectada desencadeia uma investigação manual…`

export default function App() {
  const [runId, setRunId] = useState<string | null>(null)
  const [briefing, setBriefing] = useState('')
  const [starting, setStarting] = useState(false)
  const [recent, setRecent] = useState<Run[]>([])

  const { run, messages, metrics, activeNode, pendingInterrupt, connection, error, resolveInterrupt } =
    useSquadRun(runId)

  useEffect(() => {
    void api.listRuns().then(setRecent).catch(() => undefined)
  }, [runId, run?.status])

  async function start() {
    setStarting(true)
    try {
      const created = await api.startRun(briefing)
      setRunId(created.id)
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="app">
      <header className="app__bar">
        <h1>Squad Console</h1>
        {run && (
          <>
            <span className={`status status--${run.status}`}>{run.status}</span>
            <code className="app__runid">{run.id}</code>
            <span className={`conn conn--${connection}`} title="Conexão do stream ao vivo">
              {connection === 'live' ? 'ao vivo' : connection === 'closed' ? 'reconectando' : '—'}
            </span>
          </>
        )}
        {metrics && (
          <span className="app__cost">
            {metrics.budget.total_spent.toLocaleString('pt-BR')} tokens · US${' '}
            {metrics.budget.total_cost_usd.toFixed(4)} · cache{' '}
            {(metrics.cache_hit_rate * 100).toFixed(0)}%
          </span>
        )}
      </header>

      {error && <div className="banner banner--error">{error}</div>}

      {run?.failure_reason && (
        <div className="banner banner--error">
          <strong>Run falhou:</strong> {run.failure_reason}
        </div>
      )}

      {/* Escalada: o squad pedindu ajuda faz parte da trilha, não é exceção
          escondida. Aparece como banner acionável. */}
      {pendingInterrupt && (
        <div className="banner banner--interrupt">
          <div>
            <strong>O squad pediu ajuda.</strong> Story “{pendingInterrupt.story_title}” após{' '}
            {pendingInterrupt.attempts} reprovação(ões).
            {pendingInterrupt.rejection_reason && <> Motivo: {pendingInterrupt.rejection_reason}</>}
          </div>
          <div className="banner__actions">
            <button type="button" onClick={() => void resolveInterrupt('retry')}>
              tentar de novo
            </button>
            <button type="button" onClick={() => void resolveInterrupt('skip')}>
              pular story
            </button>
            <button type="button" onClick={() => void resolveInterrupt('finish')}>
              encerrar run
            </button>
          </div>
        </div>
      )}

      {!runId ? (
        <main className="launcher">
          <h2>Acionar o squad</h2>
          <p className="muted">
            O time humano entra só aqui, com o briefing. O squad faz o resto.
          </p>
          <textarea
            value={briefing}
            onChange={(event) => setBriefing(event.target.value)}
            placeholder={BRIEFING_PLACEHOLDER}
            rows={14}
          />
          <button
            type="button"
            className="launcher__go"
            onClick={() => void start()}
            disabled={briefing.trim().length < 20 || starting}
          >
            {starting ? 'acionando…' : 'acionar squad'}
          </button>

          {recent.length > 0 && (
            <section className="launcher__recent">
              <h3>Runs recentes</h3>
              <ul>
                {recent.map((item) => (
                  <li key={item.id}>
                    <button type="button" onClick={() => setRunId(item.id)}>
                      <code>{item.id}</code>
                      <span className={`status status--${item.status}`}>{item.status}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </main>
      ) : (
        <main className="workspace">
          <Timeline runId={runId} messages={messages} activeNode={activeNode} />
          <aside className="workspace__side">
            {metrics && (
              <section className="panel">
                <h2>Consumo por agente</h2>
                <ul className="meter">
                  {Object.entries(metrics.budget.spent_by_agent)
                    .sort(([, a], [, b]) => b - a)
                    .map(([agent, tokens]) => (
                      <li key={agent}>
                        <span>{agent}</span>
                        <strong>{tokens.toLocaleString('pt-BR')}</strong>
                      </li>
                    ))}
                </ul>
                <p className="muted">
                  {metrics.calls_total} chamadas · latência média {metrics.latency_ms_avg} ms
                </p>
              </section>
            )}
            <Deliverables runId={runId} refreshKey={messages.length} />
          </aside>
        </main>
      )}
    </div>
  )
}
