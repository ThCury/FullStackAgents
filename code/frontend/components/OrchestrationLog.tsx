export type LogEntry = {
  author: string;
  content: string;
  ts: string;
};

export function OrchestrationLog({ entries }: { entries: LogEntry[] }) {
  return (
    <section className="orchestration-log">
      <h2>Log de orquestração</h2>
      {entries.length === 0 ? (
        <ol>
          <li className="empty">Nenhuma demanda enviada ainda.</li>
        </ol>
      ) : (
        <ol>
          {entries.map((entry, index) => (
            <li key={index}>
              <span className="meta">
                {entry.author} · {entry.ts}
              </span>
              {entry.content}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
