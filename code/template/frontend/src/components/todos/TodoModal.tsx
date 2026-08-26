import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Stack, Switch, TextField } from '@mui/material'
import { FormEvent, useEffect, useState } from 'react'

import { Todo, TodoInput } from '../../services/api'

type TodoModalProps = { open: boolean; todo: Todo | null; onClose: () => void; onSave: (payload: TodoInput) => Promise<void> }

const emptyTodo: TodoInput = { title: '', description: '', scheduled_time: null, repeats_daily: false }

export function TodoModal({ open, todo, onClose, onSave }: TodoModalProps) {
  const [form, setForm] = useState<TodoInput>(emptyTodo)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => { if (open) { setForm(todo ? { title: todo.title, description: todo.description, scheduled_time: todo.scheduled_time, repeats_daily: todo.repeats_daily } : emptyTodo); setError(null) } }, [open, todo])
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null)
    try { await onSave({ ...form, title: form.title.trim(), description: form.description.trim() }); onClose() } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível salvar a tarefa.') } finally { setSaving(false) }
  }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" PaperProps={{ component: 'form', onSubmit: submit }}><DialogTitle>{todo ? 'Editar tarefa' : 'Nova tarefa'}</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}>{error && <Alert severity="error">{error}</Alert>}<TextField label="Título" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required autoFocus /><TextField label="Descrição" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} multiline minRows={3} inputProps={{ maxLength: 1000 }} /><TextField label="Horário" type="time" value={form.scheduled_time ?? ''} onChange={(event) => setForm({ ...form, scheduled_time: event.target.value || null })} slotProps={{ inputLabel: { shrink: true } }} /><FormControlLabel control={<Switch checked={form.repeats_daily} onChange={(event) => setForm({ ...form, repeats_daily: event.target.checked })} />} label="Repetir todos os dias" /></Stack></DialogContent><DialogActions><Button onClick={onClose}>Cancelar</Button><Button type="submit" variant="contained" disabled={saving}>Salvar</Button></DialogActions></Dialog>
}
