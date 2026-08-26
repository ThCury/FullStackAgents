import { Alert, Box, Container, Paper, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

import { Footer } from '../../components/footer/Footer'
import { Navbar } from '../../components/navbar/Navbar'
import { Sidebar } from '../../components/sidebar/Sidebar'
import { TodoForm } from '../../components/todos/TodoForm'
import { TodoList } from '../../components/todos/TodoList'
import { api, Todo, User } from '../../services/api'

type DashboardPageProps = { token: string; onLogout: () => void }

export function DashboardPage({ token, onLogout }: DashboardPageProps) {
  const [user, setUser] = useState<User | null>(null)
  const [todos, setTodos] = useState<Todo[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { Promise.all([api.me(token), api.listTodos(token)]).then(([currentUser, currentTodos]) => { setUser(currentUser); setTodos(currentTodos) }).catch(onLogout) }, [token, onLogout])
  async function createTodo(title: string) { try { const todo = await api.createTodo(title, token); setTodos((items) => [...items, todo]) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível criar a tarefa.') } }
  async function toggleTodo(todo: Todo) { try { const updated = await api.updateTodo({ ...todo, completed: !todo.completed }, token); setTodos((items) => items.map((item) => item.id === updated.id ? updated : item)) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível atualizar a tarefa.') } }
  async function deleteTodo(todoId: number) { try { await api.deleteTodo(todoId, token); setTodos((items) => items.filter((item) => item.id !== todoId)) } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível excluir a tarefa.') } }
  if (user === null) return null
  return <Box minHeight="100vh" display="flex" flexDirection="column"><Navbar email={user.email} onLogout={onLogout} /><Box display="flex" flexGrow={1}><Sidebar /><Container component="main" maxWidth="md" sx={{ py: 4 }}><Paper elevation={2} sx={{ p: 3 }}><Typography component="h1" variant="h4" gutterBottom>Suas tarefas</Typography><Typography color="text.secondary" sx={{ mb: 3 }}>Planeje, conclua e acompanhe o que importa.</Typography>{error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}<TodoForm onCreate={createTodo} /><TodoList todos={todos} onToggle={toggleTodo} onDelete={deleteTodo} /></Paper></Container></Box><Footer /></Box>
}
