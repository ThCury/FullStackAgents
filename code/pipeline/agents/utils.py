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


def looks_like_json(text: str) -> bool:
    """Versão booleana de `extract_json`, para usar como validação de
    resposta final em `BaseAgent.call_with_tools` (sem lançar exceção)."""
    try:
        extract_json(text)
        return True
    except ValueError:
        return False


def written_files(transcript: list[dict]) -> list[str]:
    """Lista os arquivos de fato escritos por chamadas a `write_file` num
    transcript de `call_with_tools`, na ordem em que ocorreram (sem
    duplicatas). Usado como fallback quando o agente não termina com uma
    resposta formal (ver `finished_cleanly` em `call_with_tools`), pra saber
    o que foi entregue mesmo sem o JSON de decisão."""
    seen: list[str] = []
    for step in transcript:
        if step.get("step") != "tool_call" or step.get("name") != "write_file":
            continue
        rel_path = step.get("input", {}).get("rel_path")
        if rel_path and rel_path not in seen:
            seen.append(rel_path)
    return seen
