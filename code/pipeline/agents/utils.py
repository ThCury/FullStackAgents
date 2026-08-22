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
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        starts = [(idx, open_char, close_char) for open_char, close_char in (("{", "}"), ("[", "]")) if (idx := candidate.find(open_char)) != -1]
        for start, open_char, close_char in sorted(starts, key=lambda item: item[0]):
            end = candidate.rfind(close_char)
            if end != -1 and end > start:
                snippet = candidate[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"Não foi possível extrair JSON válido da resposta:\n{text[:500]}")
