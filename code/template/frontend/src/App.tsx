import { useCallback, useState } from 'react'

import { AppPage } from './components/sidebar/Sidebar'
import { AuthPage } from './pages/auth/AuthPage'
import { DashboardPage } from './pages/dashboard/DashboardPage'
import { ProfilePage } from './pages/profile/ProfilePage'

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const [page, setPage] = useState<AppPage>('tasks')
  const logout = useCallback(() => { localStorage.removeItem('access_token'); setToken(null); setPage('tasks') }, [])
  const authenticate = useCallback((newToken: string) => { localStorage.setItem('access_token', newToken); setToken(newToken); setPage('tasks') }, [])
  if (!token) return <AuthPage onAuthenticated={authenticate} />
  return page === 'profile' ? <ProfilePage token={token} onLogout={logout} onNavigate={setPage} /> : <DashboardPage token={token} onLogout={logout} onNavigate={setPage} />
}
