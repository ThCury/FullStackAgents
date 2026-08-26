import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'

import { User } from '../../services/api'

type ProfileModalProps = { open: boolean; user: User; onClose: () => void; onSave: (profile: Pick<User, 'name' | 'email'>) => Promise<void> }

export function ProfileModal({ open, user, onClose, onSave }: ProfileModalProps) {
  const [name, setName] = useState(user.name)
  const [email, setEmail] = useState(user.email)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setName(user.name); setEmail(user.email); setError(null) } }, [open, user])
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null)
    try { await onSave({ name: name.trim(), email: email.trim() }); onClose() } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível salvar o perfil.') } finally { setSaving(false) }
  }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs" PaperProps={{ component: 'form', onSubmit: submit }}><DialogTitle>Editar perfil</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{error && <Alert severity="error">{error}</Alert>}<TextField label="Nome" value={name} onChange={(event) => setName(event.target.value)} required autoFocus /><TextField label="E-mail" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></Stack></DialogContent><DialogActions><Button onClick={onClose}>Cancelar</Button><Button type="submit" variant="contained" disabled={saving}>Salvar</Button></DialogActions></Dialog>
}
