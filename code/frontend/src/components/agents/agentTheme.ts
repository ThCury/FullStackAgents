import type { AgentStatus } from '@/utils/runMapper'

export interface AgentTheme {
  lineColor: string
  trackColor: string
  iconColor: string
  labelColor: string
  borderColor: string
  nodeGradient: string
  nodeShadow: string
  pulse: boolean
}

const ACCENT = '#a3e635'
const MUTED = '#52525b'
const DANGER = '#f87171'

export function themeFor(status: AgentStatus): AgentTheme {
  if (status === 'done') {
    return {
      lineColor: ACCENT,
      trackColor: 'rgba(163,230,53,0.25)',
      iconColor: ACCENT,
      labelColor: ACCENT,
      borderColor: 'rgba(163,230,53,0.3)',
      nodeGradient: 'linear-gradient(to bottom, rgba(163,230,53,0.6), rgba(163,230,53,0))',
      nodeShadow: '0 0 24px -6px rgba(163,230,53,0.5)',
      pulse: false,
    }
  }
  if (status === 'running') {
    return {
      lineColor: ACCENT,
      trackColor: 'rgba(163,230,53,0.25)',
      iconColor: ACCENT,
      labelColor: ACCENT,
      borderColor: 'rgba(163,230,53,0.45)',
      nodeGradient: 'linear-gradient(to bottom, rgba(163,230,53,0.8), rgba(163,230,53,0))',
      nodeShadow: '0 0 30px -6px rgba(163,230,53,0.7)',
      pulse: true,
    }
  }
  if (status === 'failed') {
    return {
      lineColor: DANGER,
      trackColor: 'rgba(248,113,113,0.25)',
      iconColor: DANGER,
      labelColor: DANGER,
      borderColor: 'rgba(248,113,113,0.35)',
      nodeGradient: 'linear-gradient(to bottom, rgba(248,113,113,0.7), rgba(248,113,113,0))',
      nodeShadow: '0 0 26px -6px rgba(248,113,113,0.6)',
      pulse: false,
    }
  }
  return {
    lineColor: MUTED,
    trackColor: 'rgba(255,255,255,0.08)',
    iconColor: MUTED,
    labelColor: MUTED,
    borderColor: '#27272a',
    nodeGradient: 'linear-gradient(to bottom, rgba(255,255,255,0.15), rgba(255,255,255,0))',
    nodeShadow: 'none',
    pulse: false,
  }
}
