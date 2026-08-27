import { useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PromptComposer } from '@/components/projects/PromptComposer'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { Badge } from '@/components/ui/Badge'
import { Alert, EmptyState, Loading } from '@/components/ui/Feedback'
import { useSession } from '@/context/SessionContext'
import { useAsync } from '@/hooks/useAsync'
import { routes } from '@/router/routes'
import { projectsApi } from '@/services/projectsApi'
import { projectNameFromPrompt } from '@/utils/format'

export function HomePage() {
  const { user } = useSession()
  const navigate = useNavigate()

  const { data, loading, error, reload } = useAsync(
    (signal) => projectsApi.list(signal),
    [],
  )

  const submit = useCallback(
    async (prompt: string) => {
      const response = await projectsApi.create({
        name: projectNameFromPrompt(prompt),
        prompt,
        requested_by_id: user?.id ?? 'local-user',
        requested_by_name: user?.name ?? 'Usuário local',
      })
      reload()
      navigate(routes.project(response.project_id))
    },
    [user, navigate, reload],
  )

  const recent = data?.projects.slice(0, 2) ?? []

  return (
    <div className="home">
      <Badge>Agentes prontos</Badge>
      <h1 className="home__headline">O que vamos construir?</h1>
      <p className="home__lede">
        Descreva a feature em linguagem natural e deixe o time de agentes cuidar do resto
      </p>

      <PromptComposer onSubmit={submit} hint="PO → Developer → Coder" />

      <section className="home__recent">
        <div className="section-head">
          <span className="eyebrow">Projetos recentes</span>
          <Link to={routes.history}>ver todos</Link>
        </div>

        {error && <Alert>{error}</Alert>}
        {loading && !data && <Loading label="Carregando projetos…" />}
        {data && recent.length === 0 && (
          <EmptyState>Nenhum projeto ainda. Envie o primeiro prompt acima.</EmptyState>
        )}
        {recent.length > 0 && (
          <div className="grid-2">
            {recent.map((project) => (
              <ProjectCard key={project.project_id} project={project} variant="tile" />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
