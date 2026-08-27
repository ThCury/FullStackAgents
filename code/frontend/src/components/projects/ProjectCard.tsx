import { useNavigate } from 'react-router-dom'
import { routes } from '@/router/routes'
import { formatDateTime, truncate } from '@/utils/format'
import type { ProjectListItem } from '@/types/api'

interface ProjectCardProps {
  project: ProjectListItem
  /** `tile` empilha (grade da home); `row` alinha nome e status (histórico). */
  variant?: 'row' | 'tile'
}

export function ProjectCard({ project, variant = 'row' }: ProjectCardProps) {
  const navigate = useNavigate()
  const isTile = variant === 'tile'

  const name = <span className="project-card__name">{truncate(project.name, isTile ? 80 : 110)}</span>
  const date = <span className="project-card__date">{formatDateTime(project.brasil_datetime)}</span>
  const status = (
    <span className="status-text" style={{ color: 'var(--accent)' }}>
      {project.status === 'ACTIVE' ? 'Ativo' : project.status}
    </span>
  )

  return (
    <button
      type="button"
      className={`card card--interactive project-card${isTile ? ' project-card--tile' : ''}`}
      onClick={() => navigate(routes.project(project.project_id))}
    >
      {isTile ? (
        <>
          {name}
          <span className="project-card__footer">
            {date}
            {status}
          </span>
        </>
      ) : (
        <>
          <span className="project-card__main">
            {name}
            {date}
          </span>
          {status}
        </>
      )}
    </button>
  )
}
