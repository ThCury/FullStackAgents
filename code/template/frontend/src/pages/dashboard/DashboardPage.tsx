import AddIcon from '@mui/icons-material/Add'
import { Alert, Box, Button, Container, Paper, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { Footer } from '../../components/footer/Footer'
import { Navbar } from '../../components/navbar/Navbar'
import { AppPage, Sidebar } from '../../components/sidebar/Sidebar'
import { TodoList } from '../../components/todos/TodoList'
import { TodoModal } from '../../components/todos/TodoModal'
import { api, Todo, TodoInput, User } from '../../services/api'

type DashboardPageProps = { token: string; onLogout: () => void; onNavigate: (page: AppPage) => void }

export function DashboardPage({ token, onLogout, onNavigate }: DashboardPageProps) {
  const [user, setUser] = useState<User | null>(null)
  const [todos, setTodos] = useState<Todo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [todoModalOpen, setTodoModalOpen] = useState(false)
  const [selectedTodo, setSelectedTodo] = useState<Todo | null>(null)
  useEffect(() => { Promise.all([api.me(token), api.listTodos(token)]).then(([currentUser, currentTodos]) => { setUser(currentUser); setTodos(currentTodos) }).catch(onLogout) }, [token, onLogout])
  function openNewTodo() { setSelectedTodo(null); setTodoModalOpen(true) }
  function openEditTodo(todo: Todo) { setSelectedTodo(todo); setTodoModalOpen(true) }
  async function saveTodo(payload: TodoInput) {
    try {
      if (selectedTodo === null) { const todo = await api.createTodo(payload, token); setTodos((items) => [...items, todo]) }
      else { const updated = await api.updateTodo(selectedTodo.id, payload, token); setTodos((items) => items.map((item) => item.id === updated.id ? updated : item)) }
    } catch (requestError) { const message = requestError instanceof Error ? requestError.message : 'Não foi possível salvar a tarefa.'; setError(message); throw new Error(message) }
  }
  async function toggleTodo(todo: Todo) { try { const updated = await api.updateTodo(todo.id, { completed: !todo.completed }, token); setTodos((items) => items.map((item) => item.id === updated.id ? updated : item)) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível atualizar a tarefa.') } }
  async function deleteTodo(todoId: number) { try { await api.deleteTodo(todoId, token); setTodos((items) => items.filter((item) => item.id !== todoId)) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível excluir a tarefa.') } }
  if (user === null) return null
  return <Box minHeight="100vh" display="flex" flexDirection="column"><Navbar name={user.name} email={user.email} onOpenProfile={() => onNavigate('profile')} onLogout={onLogout} /><Box display="flex" minHeight="calc(100vh - 64px)"><Sidebar activePage="tasks" onNavigate={onNavigate} /><Container component="main" maxWidth="md" sx={{ py: 4 }}><Paper elevation={2} sx={{ p: 3 }}><Box display="flex" alignItems="center" justifyContent="space-between" gap={2} mb={3}><Box><Typography component="h1" variant="h4" gutterBottom>Suas tarefas</Typography><Typography color="text.secondary">Planeje, conclua e acompanhe o que importa.</Typography></Box><Button variant="contained" startIcon={<AddIcon />} onClick={openNewTodo}>Nova tarefa</Button></Box>{error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}<TodoList todos={todos} onToggle={toggleTodo} onEdit={openEditTodo} onDelete={deleteTodo} /></Paper></Container></Box><Footer /><TodoModal open={todoModalOpen} todo={selectedTodo} onClose={() => setTodoModalOpen(false)} onSave={saveTodo} /></Box>
}
