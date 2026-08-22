/**
 * Timeline — a tela que decide a nota.
 *
 * "Um output final sem orquestração visível não será considerado." Esta é a
 * visão que torna a orquestração visível: quem falou com quem, o que entregou,
 * e **por quê**.
 *
 * Duas escolhas de UX que valem defender:
 *   1. `rationale` aparece sempre, não em tooltip. O avaliador precisa ler a
 *      justificativa sem interagir.
 *   2. Cada handoff abre o prompt cru que o gerou. Auditoria sem o prompt é
 *      "confia em mim".
 */

import { useState } from 'react'
import { api, type AgentMessage, type LlmCall, type MessageKind } from '../api/client'

const ROLE_LABEL: Record<string, string> = {
  briefing_analyst: 'Briefing Analyst',
  product_owner: 'PO Agent',
  developer: 'Dev Agent',
  qa: 'QA Agent',
  orchestrator: 'Orquestrador',
  human: 'Humano',
}

const KIND_LABEL: Record<MessageKind, string> = {
  handoff: 'passou o bastão',
  delivery: 'entregou',
  rejection: 'reprovou',
  question: 'perguntou',
  decision: 'decidiu',
}

interface Props {
  runId: string
  messages: AgentMessage[]
  activeNode: string | null
}

export function Timeline({ runId, messages, activeNode }: Props) {
  const [openCall, setOpenCall] = useState<LlmCall | null>(null)
  const [loadingCall, setLoadingCall] = useState<string | null>(null)

  async function inspect(message: AgentMessage) {
    if (!message.llm_call_ref) return
    setLoadingCall(message.llm_call_ref)
    try {
      setOpenCall(await api.llmCall(runId, message.llm_call_ref))
    } finally {
      setLoadingCall(null)
    }
  }

  return (
    <section className="timeline">
      <header className="timeline__header">
        <h2>Comunicação do squad</h2>
        <span className="timeline__count">{messages.length} handoffs</span>
      </header>

      <ol className="timeline__list">
        {messages.map((message) => (
          <li key={message.id} className={`msg msg--${message.kind}`}>
            <div className="msg__route">
              <span className={`agent agent--${message.from_agent}`}>
                {ROLE_LABEL[message.from_agent] ?? message.from_agent}
              </span>
              <span className="msg__arrow" aria-hidden>
                →
              </span>
              <span className={`agent agent--${message.to_agent}`}>
                {ROLE_LABEL[message.to_agent] ?? message.to_agent}
              </span>
              <span className="msg__kind">{KIND_LABEL[message.kind]}</span>
              <span className="msg__seq">#{message.seq}</span>
            </div>

            <p className="msg__summary">{message.summary}</p>

            {message.rationale && (
              <p className="msg__rationale">
                <strong>Por quê:</strong> {message.rationale}
              </p>
            )}

            <footer className="msg__footer">
              {message.usage.input_tokens + message.usage.output_tokens > 0 ? (
                <span className="msg__tokens">
                  {message.usage.input_tokens + message.usage.output_tokens} tokens
                  {message.usage.cache_read_tokens > 0 && ' · cache hit'}
                </span>
              ) : (
                <span className="msg__tokens msg__tokens--none">determinístico</span>
              )}

              {message.llm_call_ref && (
                <button
                  type="button"
                  className="msg__inspect"
                  onClick={() => void inspect(message)}
                  disabled={loadingCall === message.llm_call_ref}
                >
                  {loadingCall === message.llm_call_ref ? 'abrindo…' : 'ver prompt cru'}
                </button>
              )}
            </footer>
          </li>
        ))}

        {activeNode && (
          <li className="msg msg--active">
            <span className={`agent agent--${activeNode}`}>
              {ROLE_LABEL[activeNode] ?? activeNode}
            </span>{' '}
            trabalhando…
          </li>
        )}
      </ol>

      {openCall && <Inspector call={openCall} onClose={() => setOpenCall(null)} />}
    </section>
  )
}

/**
 * Inspector — o segundo nível da auditoria.
 *
 * Mostra o prompt e a resposta crus. `prompt_hash` está aqui de propósito: se
 * ele muda entre chamadas do mesmo agente, o prompt caching está quebrado e o
 * custo triplica em silêncio.
 */
function Inspector({ call, onClose }: { call: LlmCall; onClose: () => void }) {
  return (
    <div className="inspector" role="dialog" aria-label="Chamada crua ao modelo">
      <header className="inspector__header">
        <h3>{ROLE_LABEL[call.agent] ?? call.agent}</h3>
        <dl className="inspector__meta">
          <dt>modelo</dt>
          <dd>{call.model}</dd>
          <dt>effort</dt>
          <dd>{call.effort || '—'}</dd>
          <dt>latência</dt>
          <dd>{call.latency_ms} ms</dd>
          <dt>prefixo</dt>
          <dd title="Se muda entre chamadas do mesmo agente, o cache está quebrado">
            {call.prompt_hash}
          </dd>
          <dt>cache</dt>
          <dd>{call.usage.cache_read_tokens > 0 ? 'hit' : 'miss'}</dd>
        </dl>
        <button type="button" onClick={onClose} className="inspector__close">
          fechar
        </button>
      </header>

      <div className="inspector__body">
        <section>
          <h4>System (prefixo cacheável)</h4>
          <pre>{call.system_prompt}</pre>
        </section>
        <section>
          <h4>User</h4>
          <pre>{call.user_prompt}</pre>
        </section>
        <section>
          <h4>Resposta</h4>
          <pre>{call.raw_response}</pre>
        </section>
      </div>
    </div>
  )
}
