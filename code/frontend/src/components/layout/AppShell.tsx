import { Outlet } from 'react-router-dom'
import { TabBar } from './TabBar'
import { TopBar } from './TopBar'

/**
 * Casca única para os dois layouts da referência: topbar no desktop e tabbar
 * no mobile. O CSS decide qual aparece — o mesmo componente serve aos dois.
 */
export function AppShell() {
  return (
    <div className="shell">
      <TopBar />
      <main className="shell__content">
        <Outlet />
      </main>
      <TabBar />
    </div>
  )
}
