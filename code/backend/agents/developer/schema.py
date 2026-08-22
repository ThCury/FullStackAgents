"""Contrato de saída do Dev - Artifact + ADR. `alternatives_considered` é
obrigatório: sem alternativas, "justificativa" vira racionalização (§5.2)."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "files_changed": {"type": "array", "items": {"type": "string"}},
        "tests_written": {"type": "array", "items": {"type": "string"}},
        "adr": {
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "context": {"type": "string"},
                "alternatives_considered": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "rationale": {"type": "string"},
                "consequences": {"type": "string"},
            },
            "required": ["decision", "context", "alternatives_considered", "rationale", "consequences"],
        },
    },
    "required": ["summary", "files_changed", "tests_written", "adr"],
}
