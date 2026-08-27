import { themeFor } from './agentTheme'
import type { AgentView } from '@/utils/runMapper'

interface AgentPipelineProps {
  agents: AgentView[]
  selectedId: string | null
  onSelect: (agentId: string) => void
  /** Estado global da run, usado para colorir o hub central. */
  active: boolean
  finished: boolean
}

const HUB_X = 450
const HUB_Y = 180
const NODE_Y = 40

/** Diagrama do fluxo (versão desktop da referência web). */
export function AgentPipeline({
  agents,
  selectedId,
  onSelect,
  active,
  finished,
}: AgentPipelineProps) {
  const hubGradient = finished
    ? 'linear-gradient(to bottom, rgba(22,101,52,0.7), rgba(22,101,52,0))'
    : active
      ? 'linear-gradient(to bottom, rgba(163,230,53,0.7), rgba(163,230,53,0))'
      : 'linear-gradient(to bottom, rgba(255,255,255,0.15), rgba(255,255,255,0))'
  const hubShadow = finished
    ? '0 0 30px -8px rgba(22,101,52,0.6)'
    : active
      ? '0 0 30px -8px rgba(163,230,53,0.6)'
      : 'none'
  return (
    <div className="pipeline only-desktop">
      <svg viewBox="0 0 900 220" className="pipeline__svg" fill="none" aria-hidden="true">
        {agents.map((agent) => {
          const theme = themeFor(agent.status)
          return (
            <g key={agent.id}>
              <line
                x1={agent.x}
                y1={NODE_Y}
                x2={HUB_X}
                y2={HUB_Y}
                stroke={theme.trackColor}
                strokeWidth={1.5}
                strokeLinecap="round"
              />
              {agent.status !== 'pending' && (
                <circle r={3.5} fill={theme.lineColor} opacity={0}>
                  <animateMotion
                    path={`M ${agent.x} ${NODE_Y} L ${HUB_X} ${HUB_Y}`}
                    dur="2.2s"
                    begin={agent.delay}
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0;1;1;0"
                    keyTimes="0;0.15;0.85;1"
                    dur="2.2s"
                    begin={agent.delay}
                    repeatCount="indefinite"
                  />
                </circle>
              )}
            </g>
          )
        })}
      </svg>

      {agents.map((agent) => {
        const theme = themeFor(agent.status)
        const selected = selectedId === agent.id
        return (
          <button
            type="button"
            key={agent.id}
            onClick={() => onSelect(agent.id)}
            title={`${agent.name} — ${agent.description}`}
            aria-pressed={selected}
            className={`pipeline__node${selected ? ' pipeline__node--selected' : ''}`}
            style={{
              left: `${((agent.x / 900) * 100).toFixed(1)}%`,
              background: theme.nodeGradient,
              boxShadow: theme.nodeShadow,
            }}
          >
            <span className="pipeline__node-inner">
              <span className="pipeline__initial" style={{ color: theme.iconColor }}>
                {agent.initial}
              </span>
              <span
                className={`pipeline__label${agent.status === 'running' ? ' status-text--running' : ''}`}
                style={{ color: theme.labelColor }}
              >
                {agent.statusLabel}
              </span>
            </span>
          </button>
        )
      })}

      <div className="pipeline__hub" style={{ background: hubGradient, boxShadow: hubShadow }}>
        <div className="pipeline__hub-inner">
          <img className="pipeline__hub-image" src="/virtual.png" alt="" />
        </div>
      </div>
    </div>
  )
}
