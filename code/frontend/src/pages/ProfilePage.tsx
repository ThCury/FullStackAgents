import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { TextField } from '@/components/ui/Field'
import { useSession } from '@/context/SessionContext'
import { routes } from '@/router/routes'
import { initialsOf } from '@/utils/format'

export function ProfilePage() {
  const { user, updateUser, signOut } = useSession()
  const navigate = useNavigate()
  const [name, setName] = useState(user?.name ?? '')

  const handleSignOut = () => {
    signOut()
    navigate(routes.login, { replace: true })
  }

  return (
    <div className="page profile">
      <div className="page__inner">
        <h1 className="page__title" style={{ marginBottom: 32 }}>
          Perfil
        </h1>

        <div className="profile__card">
          <div className="profile__avatar" aria-hidden="true">
            {initialsOf(user?.name)}
          </div>
          <span className="profile__hint">Identificação usada para assinar as execuções</span>

          <TextField
            label="Nome"
            value={name}
            onChange={(event) => setName(event.target.value)}
            onBlur={() => updateUser({ name: name.trim() || user?.name })}
          />
          <TextField label="E-mail" value={user?.email ?? ''} readOnly />

          <Button variant="danger" block onClick={handleSignOut}>
            Sair da conta
          </Button>
        </div>
      </div>
    </div>
  )
}
