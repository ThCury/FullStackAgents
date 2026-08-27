import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useSession } from '@/context/SessionContext'
import { routes } from './routes'

export function ProtectedRoute() {
  const { user } = useSession()
  const location = useLocation()

  if (!user) {
    return <Navigate to={routes.login} replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
