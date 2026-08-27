import { SessionProvider } from '@/context/SessionContext'
import { AppRouter } from '@/router/AppRouter'

export default function App() {
  return (
    <SessionProvider>
      <AppRouter />
    </SessionProvider>
  )
}
