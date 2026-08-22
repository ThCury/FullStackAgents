import json

from .schema import OUTPUT_SCHEMA

SYSTEM_PROMPT = f"""\
Gere user stories (máx 2) para o escopo do briefing.

Para cada story:
- id: US-NN
- title: nome curto
- description: "Como <papel>, quero <ação>, para <benefício>"
- priority: must/should/could/wont
- scenario_tag: tag do fluxo
- acceptance_criteria: 2-3 Gherkin (given/when/then)

Resolva perguntas abertas do briefing. Cobertura mínima: caminho feliz + 1 validação.

Responda SOMENTE JSON:

{json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)}
"""
