export type User = { id: number; email: string; name: string }
export type Todo = { id: number; title: string; description: string; scheduled_time: string | null; repeats_daily: boolean; completed: boolean }
export type TodoInput = Pick<Todo, 'title' | 'description' | 'scheduled_time' | 'repeats_daily'>

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
  updateProfile: (profile: Pick<User, 'name' | 'email'>, token: string) => request<User>('/profile', { method: 'PATCH', body: JSON.stringify(profile) }, token),
  listTodos: (token: string) => request<Todo[]>('/todos', {}, token),
  createTodo: (payload: TodoInput, token: string) => request<Todo>('/todos', { method: 'POST', body: JSON.stringify(payload) }, token),
  updateTodo: (todoId: number, payload: Partial<TodoInput & Pick<Todo, 'completed'>>, token: string) => request<Todo>(`/todos/${todoId}`, { method: 'PATCH', body: JSON.stringify(payload) }, token),
  deleteTodo: (todoId: number, token: string) => request<void>(`/todos/${todoId}`, { method: 'DELETE' }, token),
}
