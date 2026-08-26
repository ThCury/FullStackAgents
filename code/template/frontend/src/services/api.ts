export type User = { id: number; email: string }
export type Todo = { id: number; title: string; completed: boolean }

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8001'

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? 'Não foi possível concluir a solicitação.')
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

export const api = {
  register: (email: string, password: string) => request<{ access_token: string }>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) => request<{ access_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: (token: string) => request<User>('/auth/me', {}, token),
  listTodos: (token: string) => request<Todo[]>('/todos', {}, token),
  createTodo: (title: string, token: string) => request<Todo>('/todos', { method: 'POST', body: JSON.stringify({ title }) }, token),
  updateTodo: (todo: Todo, token: string) => request<Todo>(`/todos/${todo.id}`, { method: 'PATCH', body: JSON.stringify({ title: todo.title, completed: todo.completed }) }, token),
  deleteTodo: (todoId: number, token: string) => request<void>(`/todos/${todoId}`, { method: 'DELETE' }, token),
}
