import json
from io import BytesIO

from app.listas_apoio import LINHAS_EQUIPAMENTO, TURNOS
from app.wsgi import application

DADOS_VALIDOS = {
    "descricao": "Vazamento de óleo na esteira",
    "linha_equipamento": LINHAS_EQUIPAMENTO[0],
    "lote": "LOTE-123",
    "turno": TURNOS[0],
    "responsavel": "João Silva",
}


def chamar_wsgi(metodo, path, corpo=None):
    corpo_bytes = b""
    headers_extra = {}
    if corpo is not None:
        corpo_bytes = json.dumps(corpo).encode("utf-8")
        headers_extra["CONTENT_LENGTH"] = str(len(corpo_bytes))
        headers_extra["CONTENT_TYPE"] = "application/json"

    environ = {
        "REQUEST_METHOD": metodo,
        "PATH_INFO": path,
        "wsgi.input": BytesIO(corpo_bytes),
        **headers_extra,
    }

    resultado = {}

    def start_response(status, headers):
        resultado["status"] = status
        resultado["headers"] = dict(headers)

    corpo_resposta = b"".join(application(environ, start_response))
    resultado["body"] = corpo_resposta
    return resultado


def test_post_nao_conformidades_com_dados_validos_retorna_201():
    resposta = chamar_wsgi("POST", "/api/nao-conformidades", DADOS_VALIDOS)

    assert resposta["status"] == "201 Created"
    dados = json.loads(resposta["body"])
    assert dados["descricao"] == DADOS_VALIDOS["descricao"]
    assert dados["criado_em"]


def test_post_nao_conformidades_sem_campo_obrigatorio_retorna_400():
    dados = dict(DADOS_VALIDOS)
    dados["descricao"] = ""

    resposta = chamar_wsgi("POST", "/api/nao-conformidades", dados)

    assert resposta["status"] == "400 Bad Request"
    corpo = json.loads(resposta["body"])
    assert "descricao" in corpo["campos"]


def test_get_nao_conformidades_lista_registros_criados():
    chamar_wsgi("POST", "/api/nao-conformidades", DADOS_VALIDOS)

    resposta = chamar_wsgi("GET", "/api/nao-conformidades")

    assert resposta["status"] == "200 OK"
    lista = json.loads(resposta["body"])
    assert len(lista) >= 1
    assert lista[0]["descricao"] == DADOS_VALIDOS["descricao"]


def test_get_config_retorna_listas_de_apoio():
    resposta = chamar_wsgi("GET", "/api/config")

    assert resposta["status"] == "200 OK"
    corpo = json.loads(resposta["body"])
    assert corpo["linhas_equipamento"] == LINHAS_EQUIPAMENTO
    assert corpo["turnos"] == TURNOS
    assert "responsaveis" in corpo


def test_rota_desconhecida_na_api_retorna_404():
    resposta = chamar_wsgi("GET", "/api/rota-inexistente")

    assert resposta["status"] == "404 Not Found"


def test_metodo_nao_permitido_em_nao_conformidades():
    resposta = chamar_wsgi("DELETE", "/api/nao-conformidades")

    assert resposta["status"] == "405 Method Not Allowed"


def test_servir_index_html_na_raiz():
    resposta = chamar_wsgi("GET", "/")

    assert resposta["status"] == "200 OK"
    assert b"<html" in resposta["body"].lower() or b"<!doctype" in resposta["body"].lower()
