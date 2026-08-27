export const routes = {
  login: '/login',
  home: '/',
  history: '/historico',
  profile: '/perfil',
  projects: '/projetos',
  project: (projectId = ':projectId') => `/projetos/${projectId}`,
} as const
