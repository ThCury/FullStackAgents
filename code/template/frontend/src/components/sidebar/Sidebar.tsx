import ChecklistIcon from '@mui/icons-material/Checklist'
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'

import { useThemeSettings } from '../../theme/ThemeSettingsProvider'

export function Sidebar() {
  const { palette } = useThemeSettings()
  return <Box component="aside" sx={{ width: { md: 220 }, p: 2, bgcolor: palette.surface, color: palette.textOnSurface }}><Typography variant="overline" sx={{ fontWeight: 700 }}>Navegação</Typography><List disablePadding><ListItemButton selected sx={{ borderRadius: 2, mt: 1 }}><ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}><ChecklistIcon /></ListItemIcon><ListItemText primary="Tarefas" /></ListItemButton></List></Box>
}
