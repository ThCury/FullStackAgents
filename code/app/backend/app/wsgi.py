"""Aplicação WSGI (biblioteca padrão) que expõe a API de não conformidades
e serve os arquivos estáticos do frontend."""
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from .listas_apoio import LINHAS_EQUIPAMENTO, RESPONSAVEIS, TURNOS
from .lotes import consultar_lote, lote_storage
from .storage import ValidationError, storage

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def _json_response(start_response, status: str, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status, headers)
    return [body]


def _read_json_body(environ):
    try:
        tamanho = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        tamanho = 0
    if tamanho <= 0:
        return {}
    raw = environ["wsgi.input"].read(tamanho)
    if not raw:
        return {}
    try:
        dados = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("Corpo da requisição não é um JSON válido.")
    if not isinstance(dados, dict):
        raise ValidationError("Corpo da requisição deve ser um objeto JSON.")
    return dados


def _handle_nao_conformidades(environ, start_response):
    metodo = environ["REQUEST_METHOD"]
    if metodo == "GET":
        return _json_response(start_response, "200 OK", storage.listar())
    if metodo == "POST":
        try:
            dados = _read_json_body(environ)
            registro = storage.registrar(dados)
        except ValidationError as erro:
            return _json_response(
                start_response,
                "400 Bad Request",
                {"erro": erro.mensagem, "campos": erro.campos},
            )
        return _json_response(start_response, "201 Created", registro)
    return _json_response(
        start_response, "405 Method Not Allowed", {"erro": "Método não permitido"}
    )


def _handle_config(environ, start_response):
    if environ["REQUEST_METHOD"] != "GET":
        return _json_response(
            start_response, "405 Method Not Allowed", {"erro": "Método não permitido"}
        )
    return _json_response(
        start_response,
        "200 OK",
        {
            "linhas_equipamento": LINHAS_EQUIPAMENTO,
            "turnos": TURNOS,
            "responsaveis": RESPONSAVEIS,
        },
    )


def _handle_lotes(environ, start_response):
    if environ["REQUEST_METHOD"] != "GET":
        return _json_response(
            start_response, "405 Method Not Allowed", {"erro": "Método não permitido"}
        )
    return _json_response(start_response, "200 OK", lote_storage.listar())


def _handle_lote_detalhe(environ, start_response, codigo: str):
    if environ["REQUEST_METHOD"] != "GET":
        return _json_response(
            start_response, "405 Method Not Allowed", {"erro": "Método não permitido"}
        )
    resultado = consultar_lote(codigo, storage.listar())
    if resultado is None:
        return _json_response(
            start_response,
            "404 Not Found",
            {"erro": f"Lote '{codigo}' não foi encontrado nos dados de apoio."},
        )
    return _json_response(start_response, "200 OK", resultado)


def _serve_static(path, start_response):
    if path == "/" or path == "":
        caminho_arquivo = FRONTEND_DIR / "index.html"
    else:
        caminho_arquivo = FRONTEND_DIR / path.lstrip("/")

    try:
        caminho_arquivo = caminho_arquivo.resolve()
        caminho_arquivo.relative_to(FRONTEND_DIR.resolve())
    except (ValueError, OSError):
        caminho_arquivo = None

    if caminho_arquivo is None or not caminho_arquivo.is_file():
        corpo = b"Not Found"
        start_response(
            "404 Not Found",
            [("Content-Type", "text/plain"), ("Content-Length", str(len(corpo)))],
        )
        return [corpo]

    tipo, _ = mimetypes.guess_type(str(caminho_arquivo))
    tipo = tipo or "application/octet-stream"
    conteudo = caminho_arquivo.read_bytes()
    start_response(
        "200 OK",
        [("Content-Type", tipo), ("Content-Length", str(len(conteudo)))],
    )
    return [conteudo]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")

    if path == "/api/nao-conformidades":
        return _handle_nao_conformidades(environ, start_response)
    if path == "/api/config":
        return _handle_config(environ, start_response)
    if path == "/api/lotes":
        return _handle_lotes(environ, start_response)
    if path.startswith("/api/lotes/"):
        codigo = unquote(path[len("/api/lotes/"):])
        return _handle_lote_detalhe(environ, start_response, codigo)
    if path.startswith("/api/"):
        return _json_response(
            start_response, "404 Not Found", {"erro": "Recurso não encontrado"}
        )

    return _serve_static(path, start_response)
