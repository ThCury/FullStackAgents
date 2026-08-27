import type { ReactNode } from 'react'

interface BadgeProps {
  children: ReactNode
  tone?: 'accent' | 'muted' | 'danger'
  dot?: boolean
}

export function Badge({ children, tone = 'accent', dot = true }: BadgeProps) {
  const toneClass = tone === 'accent' ? '' : `badge--${tone}`
  return (
    <span className={['badge', toneClass].filter(Boolean).join(' ')}>
      {dot && <span className="badge__dot" aria-hidden="true" />}
      {children}
    </span>
  )
}
