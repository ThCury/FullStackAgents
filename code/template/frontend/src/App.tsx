import { useCallback, useState } from 'react'

import { AuthPage } from './pages/auth/AuthPage'
import { DashboardPage } from './pages/dashboard/DashboardPage'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const logout = useCallback(() => { localStorage.removeItem('access_token'); setToken(null) }, [])
  const authenticate = useCallback((newToken: string) => { localStorage.setItem('access_token', newToken); setToken(newToken) }, [])
  return token ? <DashboardPage token={token} onLogout={logout} /> : <AuthPage onAuthenticated={authenticate} />
}
