import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

/**
 * O backend ainda não expõe autenticação: ele só recebe `requested_by_id` /
 * `requested_by_name` em cada comando. A sessão aqui é local (localStorage) e
 * serve para identificar quem disparou a run — não é um login de verdade.
 */
export interface SessionUser {
  id: string
  name: string
  email: string
}

interface SessionContextValue {
  user: SessionUser | null
  signIn: (email: string, name?: string) => void
  updateUser: (patch: Partial<SessionUser>) => void
  signOut: () => void
}

const STORAGE_KEY = 'fsa.session'

const SessionContext = createContext<SessionContextValue | null>(null)

function readStoredUser(): SessionUser | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SessionUser) : null
  } catch {
    return null
  }
}

function persist(user: SessionUser | null): void {
  try {
    if (user) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Navegação privada ou storage bloqueado: a sessão vive só em memória.
  }
}

function nameFromEmail(email: string): string {
  const local = email.split('@')[0] ?? 'usuario'
  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(() => readStoredUser())

  const signIn = useCallback((email: string, name?: string) => {
    const next: SessionUser = {
      id: email.trim().toLowerCase(),
      email: email.trim().toLowerCase(),
      name: name?.trim() || nameFromEmail(email),
    }
    persist(next)
    setUser(next)
  }, [])

  const updateUser = useCallback((patch: Partial<SessionUser>) => {
    setUser((current) => {
      if (!current) return current
      const next = { ...current, ...patch }
      persist(next)
      return next
    })
  }, [])

  const signOut = useCallback(() => {
    persist(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, signIn, updateUser, signOut }),
    [user, signIn, updateUser, signOut],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession precisa estar dentro de <SessionProvider>.')
  return context
}
