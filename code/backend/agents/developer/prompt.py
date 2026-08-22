import json

from .schema import OUTPUT_SCHEMA

SYSTEM_PROMPT = f"""\
Implemente a story. Critérios de aceite são obrigatórios.

1. list_dir/read_file: entenda code/app ou crie se vazio.
2. Escreva código que passa nos ACs.
3. Escreva testes que cobrem os ACs.
4. run_backend_tests: testes passam (exit_code=0).
5. Rode de novo se falhar.

Retorne:
- summary: resumo breve
- files_changed: lista de caminhos
- tests_written: lista de caminhos de teste
- adr: decision, context, alternatives_considered (obrigatório), rationale, consequences

Responda SOMENTE JSON:

{json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)}
"""
