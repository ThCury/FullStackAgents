import { useCallback, useEffect, useRef, useState } from 'react'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Executa um fetch e opcionalmente refaz em intervalo enquanto `pollWhile`
 * devolver true para o dado atual (usado para acompanhar runs em execução).
 */
export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  options: { pollIntervalMs?: number; pollWhile?: (data: T) => boolean } = {},
) {
  const { pollIntervalMs, pollWhile } = options
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const pollWhileRef = useRef(pollWhile)
  pollWhileRef.current = pollWhile

  const [reloadToken, setReloadToken] = useState(0)
  const reload = useCallback(() => setReloadToken((token) => token + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    let timer: number | undefined
    let cancelled = false

    const run = async (silent: boolean) => {
      if (!silent) setState((current) => ({ ...current, loading: true, error: null }))
      try {
        const data = await loader(controller.signal)
        if (cancelled) return
        setState({ data, loading: false, error: null })
        const keepPolling = pollIntervalMs && pollWhileRef.current?.(data)
        if (keepPolling) timer = window.setTimeout(() => run(true), pollIntervalMs)
      } catch (error) {
        if (cancelled || (error instanceof DOMException && error.name === 'AbortError')) return
        setState((current) => ({
          data: current.data,
          loading: false,
          error: error instanceof Error ? error.message : 'Erro inesperado.',
        }))
      }
    }

    void run(false)

    return () => {
      cancelled = true
      controller.abort()
      if (timer) window.clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken, pollIntervalMs])

  return { ...state, reload }
}
