import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { ExecutionPage } from '@/pages/ExecutionPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { ProtectedRoute } from './ProtectedRoute'
import { routes } from './routes'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={routes.login} element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path={routes.home} element={<HomePage />} />
            <Route path={routes.history} element={<HistoryPage />} />
            <Route path={routes.profile} element={<ProfilePage />} />
            <Route path={routes.project()} element={<ExecutionPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to={routes.home} replace />} />
      </Routes>
    </BrowserRouter>
  )
}
