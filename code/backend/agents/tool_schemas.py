"""Definições de tools (formato Anthropic tool-use), compartilhadas pelos
agentes que precisam delas. ISP na prática: o Analyst e o PO só recebem
READ_ONLY_TOOLS - a capacidade de escrita nem existe do lado deles."""

READ_FILE = {
    "name": "read_file",
    "description": "Lê o conteúdo de um arquivo dentro de code/app. Caminho relativo a code/app.",
    "input_schema": {
        "type": "object",
        "properties": {"rel_path": {"type": "string", "description": "Caminho relativo, ex: backend/app/main.py"}},
        "required": ["rel_path"],
    },
}

LIST_DIR = {
    "name": "list_dir",
    "description": "Lista arquivos e diretórios dentro de code/app, recursivamente, a partir de um caminho relativo.",
    "input_schema": {
        "type": "object",
        "properties": {"rel_path": {"type": "string", "description": "Caminho relativo, use '.' para a raiz de code/app"}},
        "required": [],
    },
}

WRITE_FILE = {
    "name": "write_file",
    "description": (
        "Cria ou sobrescreve um arquivo dentro de code/app com o conteúdo fornecido. "
        "Cria diretórios intermediários automaticamente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rel_path": {"type": "string", "description": "Caminho relativo, ex: backend/app/routers/nonconformities.py"},
            "content": {"type": "string", "description": "Conteúdo completo do arquivo"},
        },
        "required": ["rel_path", "content"],
    },
}

RUN_BACKEND_TESTS = {
    "name": "run_backend_tests",
    "description": (
        "Executa a suíte pytest do backend em code/app/backend dentro de um container Docker "
        "isolado (sem rede) e retorna o resultado."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"rel_path": {"type": "string", "description": "Subdiretório do backend dentro de code/app (padrão: 'backend')"}},
        "required": [],
    },
}

RUN_FRONTEND_TESTS = {
    "name": "run_frontend_tests",
    "description": "Executa a suíte de testes do frontend em code/app/frontend dentro de um container Docker isolado.",
    "input_schema": {
        "type": "object",
        "properties": {"rel_path": {"type": "string", "description": "Subdiretório do frontend dentro de code/app (padrão: 'frontend')"}},
        "required": [],
    },
}

READ_ONLY_TOOLS = [READ_FILE, LIST_DIR]
DEV_TOOLS = [READ_FILE, LIST_DIR, WRITE_FILE, RUN_BACKEND_TESTS]
QA_TOOLS = [READ_FILE, LIST_DIR, RUN_BACKEND_TESTS, RUN_FRONTEND_TESTS]
