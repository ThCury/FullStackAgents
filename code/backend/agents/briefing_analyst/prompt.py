import json

from .schema import OUTPUT_SCHEMA

SYSTEM_PROMPT = f"""\
Estruture o briefing em campos. Nenhuma interpretação.

Extraia:
- company: nome
- pains: lista (máx 5)
- constraints: lista (máx 5)
- actors: papéis/pessoas (máx 5)
- glossary: dicionário de termos
- open_questions: perguntas abertas (máx 5)
- methodology_refs: normas citadas (máx 3)
- existing_app_notes: "vazio" ou lista do que existe em code/app

Não escreva stories. Não interprete.

Responda SOMENTE JSON:

{json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)}
"""
