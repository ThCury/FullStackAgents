import AddIcon from '@mui/icons-material/Add'
import { Box, Button, TextField } from '@mui/material'
import { FormEvent, useState } from 'react'

type TodoFormProps = { onCreate: (title: string) => Promise<void> }

export function TodoForm({ onCreate }: TodoFormProps) {
  const [title, setTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!title.trim()) return
    setSubmitting(true)
    try { await onCreate(title.trim()); setTitle('') } finally { setSubmitting(false) }
  }
  return <Box component="form" onSubmit={submit} sx={{ display: 'flex', gap: 1 }}><TextField fullWidth label="Nova tarefa" value={title} onChange={(event) => setTitle(event.target.value)} /><Button type="submit" variant="contained" disabled={submitting} startIcon={<AddIcon />}>Adicionar</Button></Box>
}
