import { useCallback, useMemo, useState } from 'react'
import { env } from '@/config/env'
import { useAsync } from '@/hooks/useAsync'
import { projectsApi } from '@/services/projectsApi'
import { runsApi } from '@/services/runsApi'
import { isRunActive, mapAgents } from '@/utils/runMapper'
import type { Project, RunFull, RunSummary } from '@/types/api'

interface ExecutionSnapshot {
  project: Project
  runs: RunSummary[]
  run: RunFull | null
}

/**
 * Carrega o projeto, a lista resumida de runs e o documento completo da run em
 * foco, mantendo o polling enquanto alguma delas estiver em andamento. O grafo
 * roda em background no backend: acompanhar o progresso é reconsultar a auditoria.
 */
export function useProjectExecution(projectId: string) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)

  const { data, loading, error, reload } = useAsync<ExecutionSnapshot>(
    async (signal) => {
      const [project, runList] = await Promise.all([
        projectsApi.get(projectId, signal),
        projectsApi.runs(projectId, signal),
      ])
      const runs = runList.runs
      const targetId = selectedRunId ?? runs[0]?._id ?? project.context.last_run_id
      const run = targetId ? await runsApi.full(targetId, signal) : null
      return { project, runs, run }
    },
    [projectId, selectedRunId],
    {
      pollIntervalMs: env.pollIntervalMs,
      pollWhile: (snapshot) =>
        isRunActive(snapshot.run?.status) || snapshot.runs.some((run) => isRunActive(run.status)),
    },
  )

  const activeRun = data?.run ?? null
  const runs = data?.runs ?? []
  const agents = useMemo(() => mapAgents(activeRun), [activeRun])
  const busy = runs.some((run) => isRunActive(run.status)) || isRunActive(activeRun?.status)

  const sendMessage = useCallback(
    async (payload: { content?: string; retryRunId?: string; userId: string; userName: string }) => {
      const response = await projectsApi.sendMessage(projectId, {
        content: payload.content,
        retry_run_id: payload.retryRunId,
        requested_by_id: payload.userId,
        requested_by_name: payload.userName,
      })
      // Volta o foco para a run mais recente e recarrega imediatamente.
      setSelectedRunId(null)
      reload()
      return response
    },
    [projectId, reload],
  )

  return {
    project: data?.project ?? null,
    runs,
    activeRun,
    agents,
    busy,
    loading,
    error,
    selectRun: setSelectedRunId,
    sendMessage,
    reload,
  }
}
