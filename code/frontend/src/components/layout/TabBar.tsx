import { NavLink, useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '@/config/navigation'

const MOBILE_LABEL: Record<string, string> = {
  home: 'Início',
  history: 'Histórico',
  profile: 'Perfil',
}

/** Barra inferior — navegação principal no mobile (referência wireframe). */
export function TabBar() {
  const location = useLocation()

  return (
    <nav className="tabbar" aria-label="Navegação principal">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `tabbar__item${isActive || item.matches?.some((path) => location.pathname.startsWith(path)) ? ' tabbar__item--active' : ''}`
          }
        >
          <span className={`tabbar__glyph tabbar__glyph--${item.glyph}`} aria-hidden="true" />
          {MOBILE_LABEL[item.glyph]}
        </NavLink>
      ))}
    </nav>
  )
}
