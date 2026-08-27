import { routes } from '@/router/routes'

export interface NavItem {
  label: string
  to: string
  /** Rotas adicionais que mantêm este item destacado. */
  matches?: string[]
  glyph: 'home' | 'history' | 'profile'
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Novo prompt', to: routes.home, matches: [routes.projects], glyph: 'home' },
  { label: 'Histórico', to: routes.history, glyph: 'history' },
  { label: 'Perfil', to: routes.profile, glyph: 'profile' },
]
