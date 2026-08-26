import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import { Avatar, Box, Button, Container, Paper, Stack, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { Footer } from '../../components/footer/Footer'
import { Navbar } from '../../components/navbar/Navbar'
import { PaletteSelector } from '../../components/palette-selector/PaletteSelector'
import { ProfileModal } from '../../components/profile/ProfileModal'
import { AppPage, Sidebar } from '../../components/sidebar/Sidebar'
import { api, User } from '../../services/api'

type ProfilePageProps = { token: string; onLogout: () => void; onNavigate: (page: AppPage) => void }

export function ProfilePage({ token, onLogout, onNavigate }: ProfilePageProps) {
  const [user, setUser] = useState<User | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  useEffect(() => { api.me(token).then(setUser).catch(onLogout) }, [token, onLogout])
  async function saveProfile(profile: Pick<User, 'name' | 'email'>) { setUser(await api.updateProfile(profile, token)) }
  if (user === null) return null
  return <Box minHeight="100vh" display="flex" flexDirection="column"><Navbar name={user.name} email={user.email} onOpenProfile={() => onNavigate('profile')} onLogout={onLogout} /><Box display="flex" minHeight="calc(100vh - 64px)"><Sidebar activePage="profile" onNavigate={onNavigate} /><Container component="main" maxWidth="md" sx={{ py: 4 }}><Stack spacing={3}><Paper elevation={2} sx={{ p: 3 }}><Box display="flex" justifyContent="space-between" alignItems="flex-start" gap={2}><Stack direction="row" spacing={2} alignItems="center"><Avatar sx={{ width: 64, height: 64, bgcolor: 'secondary.main', fontSize: 26 }}>{user.name.slice(0, 1).toUpperCase()}</Avatar><Box><Typography component="h1" variant="h4">{user.name}</Typography><Typography color="text.secondary">{user.email}</Typography></Box></Stack><Button variant="contained" startIcon={<EditOutlinedIcon />} onClick={() => setModalOpen(true)}>Editar perfil</Button></Box></Paper><Paper elevation={1} sx={{ p: 3 }}><Typography variant="h6" gutterBottom>Preferências visuais</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Escolha a paleta usada no seu ambiente. A preferência fica salva neste navegador.</Typography><PaletteSelector /></Paper></Stack></Container></Box><Footer /><ProfileModal open={modalOpen} user={user} onClose={() => setModalOpen(false)} onSave={saveProfile} /></Box>
}
