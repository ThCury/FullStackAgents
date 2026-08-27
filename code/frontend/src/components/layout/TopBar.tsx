import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { NAV_ITEMS } from '@/config/navigation'
import { useSession } from '@/context/SessionContext'
import { routes } from '@/router/routes'
import { initialsOf } from '@/utils/format'
import { Brand } from './Brand'

export function TopBar() {
  const { user } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const onProfile = location.pathname === routes.profile

  return (
    <header className="topbar">
      <div className="topbar__left">
        <Link to={routes.home} aria-label="Início">
          <Brand />
        </Link>
        <nav className="nav">
          {NAV_ITEMS.filter((item) => item.glyph !== 'profile').map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav__link${isActive || item.matches?.some((path) => location.pathname.startsWith(path)) ? ' nav__link--active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <button
        type="button"
        className={`avatar-button${onProfile ? ' avatar-button--active' : ''}`}
        onClick={() => navigate(routes.profile)}
        aria-label="Abrir perfil"
      >
        {initialsOf(user?.name)}
      </button>
    </header>
  )
}
