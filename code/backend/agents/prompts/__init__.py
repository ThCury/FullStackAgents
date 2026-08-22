"""Carregador de prompts.

Prompts vivem em `.md` ao lado deste módulo, não embutidos em string Python.
Três razões:
  1. PO/QA humano consegue ler e revisar em PR sem ler código.
  2. Diff de prompt fica legível — mudança de prompt é mudança de comportamento.
  3. O texto é o prefixo estável da chamada, cacheável (§8.4). Ler de arquivo
     torna óbvio que ele não deve conter nada volátil (data, id, contador).

O cache em memória é intencional: reler o arquivo a cada chamada não muda o
conteúdo, mas atrapalha o raciocínio sobre estabilidade do prefixo.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Carrega `<name>.md`. Falha alto: prompt faltando é erro de deploy."""
    path = _PROMPT_DIR / f"{name}.md"
    if not path.is_file():
        available = sorted(p.stem for p in _PROMPT_DIR.glob("*.md"))
        raise FileNotFoundError(
            f"prompt '{name}' não encontrado em {_PROMPT_DIR}. Disponíveis: {available}"
        )
    return path.read_text(encoding="utf-8").strip()
