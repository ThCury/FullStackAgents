import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Brand } from '@/components/layout/Brand'
import { Button } from '@/components/ui/Button'
import { TextField } from '@/components/ui/Field'
import { useSession } from '@/context/SessionContext'
import { routes } from '@/router/routes'

/**
 * Identificação local: o backend ainda não tem autenticação, apenas recebe
 * `requested_by_id` / `requested_by_name` em cada comando. Nenhuma senha é
 * enviada ou armazenada — o campo existe só para casar com a referência.
 */
export function LoginPage() {
  const { user, signIn } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (user) return <Navigate to={routes.home} replace />

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError('Informe um e-mail válido.')
      return
    }
    signIn(email)
    navigate(routes.home, { replace: true })
  }

  return (
    <div className="login">
      <form className="login__card" onSubmit={handleSubmit}>
        <Brand size="lg" />
        <div>
          <h1 className="login__title">Bem-vindo de volta</h1>
          <p className="login__subtitle">Entre para orquestrar seus agentes de IA</p>
        </div>
        <TextField
          label="E-mail"
          type="email"
          autoComplete="email"
          placeholder="voce@empresa.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value)
            setError(null)
          }}
          error={error}
        />
        <Button type="submit" block>
          Entrar
        </Button>
        <p className="login__footnote">
          Identificação local — o backend ainda não exige senha. Seu e-mail é usado apenas para
          assinar as execuções.
        </p>
      </form>
    </div>
  )
}
