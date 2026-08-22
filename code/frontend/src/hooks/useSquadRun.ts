/**
 * Acompanha um run: histórico durável + tempo real.
 *
 * O padrão importa e é o mesmo que o backend assume (§8):
 *   - `/timeline` é a fonte da verdade (append-only, sobrevive a reconexão)
 *   - o SSE é só o gatilho de "chegou algo novo"
 *
 * Por isso não acumulamos estado a partir do evento SSE: ao receber um evento
 * de mensagem, buscamos o delta por `since_seq`. Se o browser perder conexão e
 * reconectar, nada é perdido e nada duplica — sem precisar de deduplicação
 * no cliente.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type AgentMessage, type Metrics, type Run } from '../api/client'

export type ConnectionState = 'idle' | 'live' | 'closed'

export interface InterruptRequest {
  story_title: string | null
  attempts: number
  rejection_reason: string | null
  required_changes: string[]
  options: string[]
}

export function useSquadRun(runId: string | null) {
  const [run, setRun] = useState<Run | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [activeNode, setActiveNode] = useState<string | null>(null)
  const [pendingInterrupt, setPendingInterrupt] = useState<InterruptRequest | null>(null)
  const [connection, setConnection] = useState<ConnectionState>('idle')
  const [error, setError] = useState<string | null>(null)

  // Última `seq` conhecida, para pedir só o delta.
  const lastSeq = useRef(-1)

  const syncTimeline = useCallback(async (id: string) => {
    const delta = await api.timeline(id, lastSeq.current)
    const last = delta.at(-1)
    if (!last) return
    lastSeq.current = last.seq
    setMessages((current) => [...current, ...delta])
  }, [])

  const refresh = useCallback(
    async (id: string) => {
      const [runData, metricsData] = await Promise.all([api.getRun(id), api.metrics(id)])
      setRun(runData)
      setMetrics(metricsData)
      await syncTimeline(id)
    },
    [syncTimeline],
  )

  useEffect(() => {
    if (!runId) return

    lastSeq.current = -1
    setMessages([])
    setPendingInterrupt(null)
    setError(null)

    let cancelled = false
    const source = new EventSource(api.streamUrl(runId))

    const onMessage = () => {
      void syncTimeline(runId).catch((e: Error) => setError(e.message))
    }

    source.addEventListener('open', () => setConnection('live'))
    source.addEventListener('message', onMessage)

    source.addEventListener('node_started', (event) => {
      const data = JSON.parse((event as MessageEvent<string>).data) as { agent?: string }
      setActiveNode(data.agent ?? null)
    })

    source.addEventListener('budget', () => {
      void api.metrics(runId).then(setMetrics).catch(() => undefined)
    })

    source.addEventListener('interrupt', (event) => {
      setPendingInterrupt(JSON.parse((event as MessageEvent<string>).data) as InterruptRequest)
    })

    const onTerminal = () => {
      setActiveNode(null)
      void refresh(runId).catch((e: Error) => setError(e.message))
    }
    source.addEventListener('run_finished', onTerminal)
    source.addEventListener('run_status', onTerminal)

    source.onerror = () => {
      // O EventSource reconecta sozinho. Só marcamos o estado para a UI avisar,
      // e fazemos um sync manual porque pode ter chegado coisa na janela caída.
      setConnection('closed')
      if (!cancelled) void syncTimeline(runId).catch(() => undefined)
    }

    // Carga inicial: cobre o caso de abrir o Console num run já em andamento
    // (ou já terminado) — o SSE só traz o que vier a partir de agora.
    void refresh(runId).catch((e: Error) => setError(e.message))

    return () => {
      cancelled = true
      source.close()
      setConnection('idle')
    }
  }, [runId, refresh, syncTimeline])

  const resolveInterrupt = useCallback(
    async (resolution: 'retry' | 'skip' | 'finish') => {
      if (!runId) return
      setPendingInterrupt(null)
      await api.resume(runId, resolution)
    },
    [runId],
  )

  return {
    run,
    messages,
    metrics,
    activeNode,
    pendingInterrupt,
    connection,
    error,
    resolveInterrupt,
  }
}
