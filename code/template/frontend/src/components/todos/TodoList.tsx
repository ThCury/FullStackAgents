import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { Checkbox, IconButton, List, ListItem, ListItemButton, ListItemText, Typography } from '@mui/material'

import { Todo } from '../../services/api'

type TodoListProps = { todos: Todo[]; onToggle: (todo: Todo) => Promise<void>; onDelete: (todoId: number) => Promise<void> }

export function TodoList({ todos, onToggle, onDelete }: TodoListProps) {
  if (todos.length === 0) return <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>Nenhuma tarefa por aqui.</Typography>
  return <List sx={{ mt: 2 }}>{todos.map((todo) => <ListItem key={todo.id} disablePadding secondaryAction={<IconButton edge="end" aria-label="Excluir tarefa" onClick={() => onDelete(todo.id)}><DeleteOutlineIcon /></IconButton>}><ListItemButton onClick={() => onToggle(todo)}><Checkbox checked={todo.completed} tabIndex={-1} /><ListItemText primary={todo.title} primaryTypographyProps={{ sx: { textDecoration: todo.completed ? 'line-through' : 'none' } }} /></ListItemButton></ListItem>)}</List>
}
