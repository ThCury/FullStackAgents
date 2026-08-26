import AccountCircleOutlinedIcon from '@mui/icons-material/AccountCircleOutlined'
import ChecklistIcon from '@mui/icons-material/Checklist'
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'

import { useThemeSettings } from '../../theme/ThemeSettingsProvider'

export type AppPage = 'tasks' | 'profile'
type SidebarProps = { activePage: AppPage; onNavigate: (page: AppPage) => void }

export function Sidebar({ activePage, onNavigate }: SidebarProps) {
  const { palette } = useThemeSettings()
  return <Box component="aside" sx={{ display: { xs: 'none', md: 'block' }, width: 220, p: 2, bgcolor: palette.surface, color: palette.textOnSurface }}><Typography variant="overline" sx={{ fontWeight: 700 }}>Navegação</Typography><List disablePadding><ListItemButton selected={activePage === 'tasks'} onClick={() => onNavigate('tasks')} sx={{ borderRadius: 2, mt: 1 }}><ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}><ChecklistIcon /></ListItemIcon><ListItemText primary="Tarefas" /></ListItemButton><ListItemButton selected={activePage === 'profile'} onClick={() => onNavigate('profile')} sx={{ borderRadius: 2, mt: 1 }}><ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}><AccountCircleOutlinedIcon /></ListItemIcon><ListItemText primary="Perfil" /></ListItemButton></List></Box>
}
