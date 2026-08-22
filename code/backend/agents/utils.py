"""Utilitário de parsing compartilhado entre os agentes concretos."""
from __future__ import annotations

import json
import re


def extract_json(text: str):
    """Extrai o primeiro bloco JSON válido de uma resposta de LLM (ignora
    texto solto antes/depois e blocos ```json fenced)."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text)

    for candidate in candidates:
        candidate = candidate.strip()
        for open_char, close_char in (("[", "]"), ("{", "}")):
            start = candidate.find(open_char)
            end = candidate.rfind(close_char)
            if start != -1 and end != -1 and end > start:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"Não foi possível extrair JSON válido da resposta:\n{text[:500]}")


def find_story(backlog: list[dict], story_id: str | None) -> dict | None:
    return next((s for s in backlog if s["id"] == story_id), None)


def last_rejection_feedback(test_reports: list[dict], story_id: str) -> str | None:
    for report in reversed(test_reports):
        if report.get("story_ref") == story_id:
            return None if report.get("verdict") == "approved" else report.get("feedback")
    return None

