/**
 * Renderiza a saída de um agente sem assumir um schema fixo: os modelos do
 * backend (ProductBacklog, DevelopmentPlan, ImplementationReport) evoluem, e
 * este componente exibe qualquer objeto/lista/texto de forma legível.
 */

const LABELS: Record<string, string> = {
  accepted: 'Aceito',
  rejection: 'Recusa',
  summary: 'Resumo',
  stories: 'Histórias',
  acceptance_criteria: 'Critérios de aceite',
  architecture_decisions: 'Decisões de arquitetura',
  tasks: 'Tarefas',
  files: 'Arquivos',
  title: 'Título',
  description: 'Descrição',
  priority: 'Prioridade',
  path: 'Caminho',
  action: 'Ação',
  reason: 'Motivo',
}

function humanize(key: string): string {
  return LABELS[key] ?? key.replace(/_/g, ' ')
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value as object).length === 0
  return false
}

function Value({ value }: { value: unknown }) {
  if (typeof value === 'boolean') return <>{value ? 'sim' : 'não'}</>
  if (typeof value === 'number') return <>{value.toLocaleString('pt-BR')}</>
  if (typeof value === 'string') return <p className="structured__text">{value}</p>

  if (Array.isArray(value)) {
    return (
      <ul className="structured__list">
        {value.map((item, index) => (
          <li key={index}>
            <Value value={item} />
          </li>
        ))}
      </ul>
    )
  }

  if (value && typeof value === 'object') {
    return (
      <div className="structured__nested">
        <ObjectRows record={value as Record<string, unknown>} />
      </div>
    )
  }

  return <>—</>
}

function ObjectRows({ record }: { record: Record<string, unknown> }) {
  const entries = Object.entries(record).filter(([, value]) => !isEmpty(value))
  if (entries.length === 0) return <p className="structured__text">Sem conteúdo.</p>
  return (
    <>
      {entries.map(([key, value]) => (
        <div className="structured__row" key={key}>
          <span className="structured__key">{humanize(key)}</span>
          <Value value={value} />
        </div>
      ))}
    </>
  )
}

export function StructuredOutput({ value, fallback }: { value: unknown; fallback?: string }) {
  if (isEmpty(value)) {
    return <p className="structured structured__text">{fallback ?? 'Sem resposta ainda.'}</p>
  }
  return (
    <div className="structured">
      <Value value={value} />
    </div>
  )
}
