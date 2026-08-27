/** Formatações de exibição. O backend já entrega datas em horário de Brasília. */

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  // Formato do backend: "26/08/2026 14:32:10" ou ISO. Mostramos dia + hora.
  const match = value.match(/^(\d{2}\/\d{2})\/\d{4}[ ,T]+(\d{2}:\d{2})/)
  if (match) return `${match[1]}, ${match[2]}`
  const parsed = new Date(value)
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  return value
}

export function formatTokens(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return value.toLocaleString('pt-BR')
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${ms} ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${Math.round(seconds % 60)}s`
}

export function initialsOf(name: string | null | undefined): string {
  const clean = (name ?? '').trim()
  if (!clean) return '··'
  const parts = clean.split(/\s+/)
  const letters = parts.length > 1 ? `${parts[0][0]}${parts[parts.length - 1][0]}` : parts[0].slice(0, 2)
  return letters.toUpperCase()
}

export function truncate(text: string, max = 90): string {
  const normalized = text.replace(/\s+/g, ' ').trim()
  return normalized.length <= max ? normalized : `${normalized.slice(0, max - 1)}…`
}

/** Deriva um nome curto de projeto a partir do prompt livre do usuário. */
export function projectNameFromPrompt(prompt: string): string {
  const normalized = prompt.replace(/\s+/g, ' ').trim()
  if (!normalized) return 'novo-projeto'
  return normalized.length <= 100 ? normalized : normalized.slice(0, 100)
}
