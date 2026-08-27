import { request } from './httpClient'
import type {
  CreateMessagePayload,
  CreateMessageResponse,
  CreateProjectPayload,
  CreateProjectResponse,
  Project,
  ProjectListItem,
  ProjectMessage,
  RunSummary,
} from '@/types/api'

export const projectsApi = {
  create(payload: CreateProjectPayload, signal?: AbortSignal) {
    return request<CreateProjectResponse>('/projects', { method: 'POST', body: payload, signal })
  },

  list(signal?: AbortSignal) {
    return request<{ total: number; projects: ProjectListItem[] }>('/projects', { signal })
  },

  get(projectId: string, signal?: AbortSignal) {
    return request<Project>(`/projects/${projectId}`, { signal })
  },

  sendMessage(projectId: string, payload: CreateMessagePayload, signal?: AbortSignal) {
    return request<CreateMessageResponse>(`/projects/${projectId}/messages`, {
      method: 'POST',
      body: payload,
      signal,
    })
  },

  messages(projectId: string, offset = 0, limit = 50, signal?: AbortSignal) {
    return request<{ project_id: string; total: number; messages: ProjectMessage[] }>(
      `/projects/${projectId}/messages?offset=${offset}&limit=${limit}`,
      { signal },
    )
  },

  /** Projeção resumida das runs do projeto, da mais nova para a mais antiga. */
  runs(projectId: string, signal?: AbortSignal) {
    return request<{ project_id: string; total: number; runs: RunSummary[] }>(
      `/projects/${projectId}/runs`,
      { signal },
    )
  },
}
