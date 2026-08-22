"""Contrato de saída do BriefingAnalyst - espelha domain.entities.NormalizedBriefing.
Guardado aqui (não só no prompt) para virar, no futuro, `output_config.format`
sem duplicar a definição (§8.4 - eliminar retry de parsing)."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "pains": {"type": "array", "items": {"type": "string"}},
        "constraints": {"type": "array", "items": {"type": "string"}},
        "actors": {"type": "array", "items": {"type": "string"}},
        "glossary": {"type": "object", "additionalProperties": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "methodology_refs": {"type": "array", "items": {"type": "string"}},
        "existing_app_notes": {"type": "string"},
    },
    "required": ["company", "pains", "constraints", "actors", "glossary", "open_questions", "methodology_refs"],
    "additionalProperties": False,
}
