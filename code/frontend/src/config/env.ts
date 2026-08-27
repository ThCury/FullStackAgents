/** Configuração de ambiente, lida uma única vez das variáveis do Vite. */
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const rawPollInterval = import.meta.env.VITE_POLL_INTERVAL_MS ?? '2500'

export const env = {
  apiBaseUrl: rawBaseUrl.replace(/\/+$/, ''),
  pollIntervalMs: Number.parseInt(rawPollInterval, 10) || 2500,
} as const
