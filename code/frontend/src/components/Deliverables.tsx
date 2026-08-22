/**
 * Os 5 entregáveis da Trilha B, em abas.
 *
 * Uma tela só, buscando de `/deliverables` numa chamada — cinco requisições em
 * cascata deixariam a tela montando aos pedaços na frente do avaliador.
 */

import { useEffect, useState } from 'react'
import { api, type Deliverables as Data } from '../api/client'

type Tab = 'backlog' | 'adrs' | 'qa' | 'artifacts'

const TABS: { id: Tab; label: string }[] = [
  { id: 'backlog', label: 'Backlog (PO)' },
  { id: 'adrs', label: 'Decisões (Dev)' },
  { id: 'qa', label: 'Relatório QA' },
  { id: 'artifacts', label: 'Código' },
]

export function Deliverables({ runId, refreshKey }: { runId: string; refreshKey: number }) {
  const [data, setData] = useState<Data | null>(null)
  const [tab, setTab] = useState<Tab>('backlog')

  useEffect(() => {
    void api.deliverables(runId).then(setData).catch(() => undefined)
  }, [runId, refreshKey])

  if (!data) return <p className="muted">Carregando entregáveis…</p>

  return (
    <section className="deliverables">
      <nav className="tabs">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={tab === id ? 'tabs__tab tabs__tab--on' : 'tabs__tab'}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === 'backlog' && (
        <div className="cards">
          {data.backlog.map((story) => (
            <article key={story.id} className="card">
              <header>
                <span className={`badge badge--${story.priority}`}>{story.priority}</span>
                {story.scenario_tag && <span className="badge">{story.scenario_tag}</span>}
                <span className="badge badge--status">{story.status}</span>
              </header>
              <h3>{story.title}</h3>
              <p className="card__narrative">{story.narrative}</p>
              <p className="card__why">
                <strong>Por que esta prioridade:</strong> {story.rationale}
              </p>
              <h4>Critérios de aceite</h4>
              <ul className="criteria">
                {story.acceptance_criteria.map((c) => (
                  <li key={c.id}>
                    <code>{c.id}</code>
                    <div>
                      <em>Dado</em> {c.given}
                      <br />
                      <em>Quando</em> {c.when}
                      <br />
                      <em>Então</em> {c.then}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}

      {tab === 'adrs' && (
        <div className="cards">
          {data.adrs.map((adr) => (
            <article key={adr.id} className="card">
              <h3>{adr.title}</h3>
              <p>
                <strong>Contexto:</strong> {adr.context}
              </p>
              <p>
                <strong>Decisão:</strong> {adr.decision}
              </p>
              {/* Alternativas em destaque: é o que separa decisão de racionalização. */}
              <h4>Alternativas consideradas</h4>
              <ul>
                {adr.alternatives_considered.map((alt) => (
                  <li key={alt}>{alt}</li>
                ))}
              </ul>
              <p>
                <strong>Justificativa:</strong> {adr.rationale}
              </p>
              <p className="muted">
                <strong>Consequências:</strong> {adr.consequences}
              </p>
            </article>
          ))}
        </div>
      )}

      {tab === 'qa' && (
        <div className="cards">
          {data.test_reports.map((report) => (
            <article
              key={report.id}
              className={`card card--${report.verdict === 'approved' ? 'ok' : 'bad'}`}
            >
              <header>
                <span className={`badge badge--${report.verdict}`}>
                  {report.verdict === 'approved' ? 'aprovada' : 'reprovada'}
                </span>
                <span className="badge">tentativa {report.attempt}</span>
              </header>
              <p>{report.summary}</p>

              {report.verdict === 'rejected' && (
                <>
                  <p>
                    <strong>Motivo:</strong> {report.rejection_reason}
                  </p>
                  <h4>Mudanças requeridas ao Dev</h4>
                  <ul>
                    {report.required_changes.map((change) => (
                      <li key={change}>{change}</li>
                    ))}
                  </ul>
                </>
              )}

              <h4>Casos executados</h4>
              <table className="cases">
                <thead>
                  <tr>
                    <th>Critério</th>
                    <th>Caso</th>
                    <th>Obtido</th>
                    <th>Evidência</th>
                  </tr>
                </thead>
                <tbody>
                  {report.cases.map((testCase) => (
                    <tr key={testCase.id} className={`case case--${testCase.outcome}`}>
                      <td>
                        <code>{testCase.criterion_ref}</code>
                      </td>
                      <td>{testCase.title}</td>
                      <td>{testCase.actual}</td>
                      <td>
                        {testCase.evidence.map((e) => e.kind).join(', ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          ))}
        </div>
      )}

      {tab === 'artifacts' && (
        <div className="cards">
          {data.artifacts.map((artifact) => (
            <article key={artifact.id} className="card">
              <header>
                <span className="badge">tentativa {artifact.attempt}</span>
              </header>
              <p className="muted">{artifact.how_to_verify}</p>
              <ul className="files">
                {artifact.files.map((file) => (
                  <li key={file.path}>
                    <code>{file.path}</code> <span className="badge">{file.kind}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
