import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import LogoutIcon from '@mui/icons-material/Logout'
import { AppBar, Box, IconButton, Toolbar, Typography } from '@mui/material'

type NavbarProps = { name: string; email: string; onOpenProfile: () => void; onLogout: () => void }

export function Navbar({ name, email, onOpenProfile, onLogout }: NavbarProps) {
  const username = name.trim() || email
  return <AppBar position="static" elevation={0}><Toolbar><Typography variant="h6" sx={{ flexGrow: 1 }}>Minhas tarefas</Typography><Box sx={{ display: { xs: 'none', md: 'block' }, textAlign: 'right', mr: 1 }}><Typography variant="body2">{username}</Typography></Box><IconButton color="inherit" onClick={onOpenProfile} aria-label="Abrir perfil"><AccountCircleIcon /></IconButton><IconButton color="inherit" onClick={onLogout} aria-label="Sair"><LogoutIcon /></IconButton></Toolbar></AppBar>
}
