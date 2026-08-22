"""Utilitários de parsing compartilhados entre agentes."""
from __future__ import annotations

import json
import re


def extract_json(text: str):
    """Extrai o primeiro bloco JSON válido de uma resposta de LLM.

    Tenta, em ordem: bloco ```json ... ```, depois o maior trecho entre o
    primeiro '{' ou '[' e o último '}' ou ']' correspondente.
    """
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
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
