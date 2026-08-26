import LogoutIcon from '@mui/icons-material/Logout'
import { AppBar, Box, IconButton, Toolbar, Typography } from '@mui/material'

import { PaletteSelector } from '../palette-selector/PaletteSelector'

type NavbarProps = { email: string; onLogout: () => void }

export function Navbar({ email, onLogout }: NavbarProps) {
  return <AppBar position="static" elevation={0}><Toolbar><Typography variant="h6" sx={{ flexGrow: 1 }}>Minhas tarefas</Typography><Box sx={{ display: { xs: 'none', sm: 'block' }, mr: 2 }}><PaletteSelector /></Box><Typography variant="body2" sx={{ mr: 1 }}>{email}</Typography><IconButton color="inherit" onClick={onLogout} aria-label="Sair"><LogoutIcon /></IconButton></Toolbar></AppBar>
}
