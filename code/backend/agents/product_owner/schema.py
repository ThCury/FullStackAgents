"""Contrato de saída do PO - lista de Story, espelhando domain.entities.story.
AC em Gherkin não é preciosismo: é o que permite ao QA gerar teste
automaticamente e ao avaliador conferir o rastro AC -> caso -> evidência."""

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "ex: US-01"},
        "title": {"type": "string"},
        "description": {"type": "string", "description": "Como <persona>, quero <ação>, para <benefício>"},
        "priority": {"type": "string", "enum": ["must", "should", "could", "wont"]},
        "scenario_tag": {"type": "string", "description": "identifica a que cenário/fluxo de negócio a story pertence"},
        "acceptance_criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "given": {"type": "string"},
                    "when": {"type": "string"},
                    "then": {"type": "string"},
                },
                "required": ["given", "when", "then"],
            },
        },
    },
    "required": ["id", "title", "description", "priority", "scenario_tag", "acceptance_criteria"],
}

OUTPUT_SCHEMA = {"type": "array", "items": STORY_SCHEMA}
