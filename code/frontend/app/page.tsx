"use client";

import { useState } from "react";
import { Launcher } from "@/components/Launcher";
import { OrchestrationLog, type LogEntry } from "@/components/OrchestrationLog";
import { streamDemanda } from "@/lib/api";

export default function Home() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);

  function appendEntry(entry: LogEntry) {
    setEntries((prev) => [...prev, entry]);
  }

  async function handleSubmit(demand: string) {
    appendEntry({
      author: "Você",
      content: demand,
      ts: new Date().toLocaleTimeString("pt-BR"),
    });

    setRunning(true);
    await streamDemanda(demand, {
      onMessage: (message) => {
        appendEntry({
          author: `${message.from_agent} → ${message.to_agent}`,
          content: message.content,
          ts: new Date(message.ts * 1000).toLocaleTimeString("pt-BR"),
        });
      },
      onDone: (summary) => {
        appendEntry({
          author: "squad",
          content: `Execução concluída (status: ${summary.status}) - ${summary.stories} stories, ${summary.qa_results.filter((r) => r.approved).length}/${summary.qa_results.length} aprovadas pelo QA.`,
          ts: new Date().toLocaleTimeString("pt-BR"),
        });
        setRunning(false);
      },
      onError: (error) => {
        appendEntry({
          author: "erro",
          content: error,
          ts: new Date().toLocaleTimeString("pt-BR"),
        });
        setRunning(false);
      },
    });
  }

  return (
    <div className="container">
      <header>
        <h1>Rivexx Squad Console</h1>
        <p>Descreva a demanda e acompanhe a orquestração dos agentes.</p>
      </header>
      <Launcher onSubmit={handleSubmit} disabled={running} />
      <OrchestrationLog entries={entries} />
    </div>
  );
}
