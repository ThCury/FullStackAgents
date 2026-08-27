import type { ReactNode } from 'react'

export function Alert({ children }: { children: ReactNode }) {
  return (
    <div className="alert" role="alert">
      {children}
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>
}

export function Loading({ label = 'Carregando…' }: { label?: string }) {
  return (
    <div className="empty-state" role="status">
      {label}
    </div>
  )
}
