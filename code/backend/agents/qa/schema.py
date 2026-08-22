"""Contrato de saída do QA - TestReport. Todo AC precisa ter >=1 caso
*executado* com resultado real (§5.2) - "parece ok" não é evidência."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approved", "rejected"]},
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "result": {"type": "string", "enum": ["pass", "fail"]},
                    "notes": {"type": "string"},
                },
                "required": ["name", "result"],
            },
        },
        "evidence": {"type": "string", "description": "saída de testes e trechos de código revisados que sustentam o veredito"},
        "feedback": {"type": "string", "description": "se reprovado, o que exatamente o Dev precisa corrigir"},
    },
    "required": ["verdict", "test_cases", "evidence", "feedback"],
}
