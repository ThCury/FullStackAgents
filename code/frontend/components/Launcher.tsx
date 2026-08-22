"use client";

import { useState } from "react";

export function Launcher({
  onSubmit,
}: {
  onSubmit: (demand: string) => void;
}) {
  const [demand, setDemand] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = demand.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setDemand("");
  }

  return (
    <form className="demand-form" onSubmit={handleSubmit}>
      <textarea
        value={demand}
        onChange={(event) => setDemand(event.target.value)}
        placeholder="Descreva a demanda para o squad de agentes..."
      />
      <button type="submit" disabled={!demand.trim()}>
        Enviar demanda
      </button>
    </form>
  );
}
