import { Alert, Box, Button, Container, Paper, Stack, TextField, Typography } from '@mui/material'
import { FormEvent, useState } from 'react'

import { PaletteSelector } from '../../components/palette-selector/PaletteSelector'
import { api } from '../../services/api'

type AuthMode = 'login' | 'register'
type AuthPageProps = { onAuthenticated: (token: string) => void }

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null)
    try { const response = mode === 'login' ? await api.login(email, password) : await api.register(email, password); onAuthenticated(response.access_token) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível autenticar.') } finally { setBusy(false) }
  }
  return <Container maxWidth="sm" sx={{ py: 10 }}><Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}><PaletteSelector /></Box><Paper elevation={3} sx={{ p: 4 }}><Typography component="h1" variant="h4" gutterBottom>Minhas tarefas</Typography><Typography color="text.secondary" sx={{ mb: 3 }}>Entre para organizar seu dia.</Typography><Box component="form" onSubmit={submit}><Stack spacing={2}>{error && <Alert severity="error">{error}</Alert>}<TextField label="E-mail" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /><TextField label="Senha" type="password" value={password} onChange={(event) => setPassword(event.target.value)} helperText="Mínimo de 8 caracteres" required /><Button type="submit" variant="contained" size="large" disabled={busy}>{mode === 'login' ? 'Entrar' : 'Criar conta'}</Button><Button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Ainda não tenho conta' : 'Já tenho uma conta'}</Button></Stack></Box></Paper></Container>
}
