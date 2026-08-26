import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import RepeatIcon from '@mui/icons-material/Repeat'
import ScheduleIcon from '@mui/icons-material/Schedule'
import { Box, Checkbox, Chip, IconButton, List, ListItem, ListItemButton, ListItemText, Stack, Typography } from '@mui/material'

import { Todo } from '../../services/api'

type TodoListProps = { todos: Todo[]; onToggle: (todo: Todo) => Promise<void>; onEdit: (todo: Todo) => void; onDelete: (todoId: number) => Promise<void> }

export function TodoList({ todos, onToggle, onEdit, onDelete }: TodoListProps) {
  if (todos.length === 0) return <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>Nenhuma tarefa por aqui.</Typography>
  return <List sx={{ mt: 2 }}>{todos.map((todo) => <ListItem key={todo.id} disablePadding secondaryAction={<Stack direction="row"><IconButton edge="end" aria-label="Editar tarefa" onClick={() => onEdit(todo)}><EditOutlinedIcon /></IconButton><IconButton edge="end" aria-label="Excluir tarefa" onClick={() => onDelete(todo.id)}><DeleteOutlineIcon /></IconButton></Stack>}><ListItemButton onClick={() => onToggle(todo)}><Checkbox checked={todo.completed} tabIndex={-1} /><ListItemText primary={todo.title} secondary={<Box component="span"><Typography component="span" variant="body2" display="block">{todo.description || 'Sem descrição'}</Typography><Stack component="span" direction="row" spacing={0.5} sx={{ mt: 0.5 }}>{todo.scheduled_time && <Chip component="span" size="small" icon={<ScheduleIcon />} label={todo.scheduled_time} />}{todo.repeats_daily && <Chip component="span" size="small" icon={<RepeatIcon />} label="Diária" />}</Stack></Box>} primaryTypographyProps={{ sx: { textDecoration: todo.completed ? 'line-through' : 'none' } }} /></ListItemButton></ListItem>)}</List>
}
