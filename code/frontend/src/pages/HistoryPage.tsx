import { ProjectCard } from '@/components/projects/ProjectCard'
import { Alert, EmptyState, Loading } from '@/components/ui/Feedback'
import { useAsync } from '@/hooks/useAsync'
import { projectsApi } from '@/services/projectsApi'

export function HistoryPage() {
  const { data, loading, error } = useAsync((signal) => projectsApi.list(signal), [])

  return (
    <div className="page">
      <div className="page__inner">
        <h1 className="page__title">Histórico</h1>
        <p className="page__subtitle" style={{ marginBottom: 32 }}>
          Todos os projetos enviados aos agentes
        </p>

        {error && <Alert>{error}</Alert>}
        {loading && !data && <Loading label="Carregando histórico…" />}
        {data && data.projects.length === 0 && (
          <EmptyState>Nada por aqui ainda. O primeiro prompt cria o primeiro projeto.</EmptyState>
        )}
        {data && data.projects.length > 0 && (
          <div className="stack">
            {data.projects.map((project) => (
              <ProjectCard key={project.project_id} project={project} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
