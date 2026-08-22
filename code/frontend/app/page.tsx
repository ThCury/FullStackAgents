"use client";

import { useState } from "react";
import { Launcher } from "@/components/Launcher";
import { OrchestrationLog, type LogEntry } from "@/components/OrchestrationLog";

export default function Home() {
  const [entries, setEntries] = useState<LogEntry[]>([]);

  function handleSubmit(demand: string) {
    setEntries((prev) => [
      ...prev,
      {
        author: "Você",
        content: demand,
        ts: new Date().toLocaleTimeString("pt-BR"),
      },
    ]);
  }

  return (
    <div className="container">
      <header>
        <h1>Rivexx Squad Console</h1>
        <p>Descreva a demanda e acompanhe a orquestração dos agentes.</p>
      </header>
      <Launcher onSubmit={handleSubmit} />
      <OrchestrationLog entries={entries} />
    </div>
  );
}
