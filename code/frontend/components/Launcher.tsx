"use client";

import { useState } from "react";

export function Launcher({
  onSubmit,
  disabled,
}: {
  onSubmit: (demand: string) => void;
  disabled?: boolean;
}) {
  const [demand, setDemand] = useState("");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = demand.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setDemand("");
  }

  return (
    <form className="demand-form" onSubmit={handleSubmit}>
      <textarea
        value={demand}
        onChange={(event) => setDemand(event.target.value)}
        placeholder="Descreva a demanda para o squad de agentes..."
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !demand.trim()}>
        {disabled ? "Squad trabalhando..." : "Enviar demanda"}
      </button>
    </form>
  );
}
