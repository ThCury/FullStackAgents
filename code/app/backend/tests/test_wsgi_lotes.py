import json
from io import BytesIO

from app.listas_apoio import LINHAS_EQUIPAMENTO, TURNOS
from app.wsgi import application


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


def test_get_lotes_lista_dados_de_apoio():
    resposta = chamar_wsgi("GET", "/api/lotes")

    assert resposta["status"] == "200 OK"
    lotes = json.loads(resposta["body"])
    assert len(lotes) >= 3
    assert "codigo" in lotes[0]


def test_get_lote_existente_retorna_dados_correlatos_e_ncs():
    resposta = chamar_wsgi("GET", "/api/lotes/LOTE-100")

    assert resposta["status"] == "200 OK"
    corpo = json.loads(resposta["body"])
    assert corpo["lote"]["codigo"] == "LOTE-100"
    assert corpo["lote"]["materia_prima"]
    assert corpo["lote"]["fornecedor"]
    assert corpo["lote"]["equipamento"]
    assert corpo["lote"]["turno"]
    assert isinstance(corpo["lote"]["operadores"], list)
    assert isinstance(corpo["correlatos"], list)
    assert len(corpo["correlatos"]) >= 1
    assert isinstance(corpo["nao_conformidades"], list)


def test_get_lote_com_busca_case_insensitive():
    resposta = chamar_wsgi("GET", "/api/lotes/lote-100")

    assert resposta["status"] == "200 OK"
    corpo = json.loads(resposta["body"])
    assert corpo["lote"]["codigo"] == "LOTE-100"


def test_get_lote_inexistente_retorna_404_com_mensagem_clara():
    resposta = chamar_wsgi("GET", "/api/lotes/LOTE-NAO-EXISTE")

    assert resposta["status"] == "404 Not Found"
    corpo = json.loads(resposta["body"])
    assert "erro" in corpo
    assert "LOTE-NAO-EXISTE" in corpo["erro"]


def test_get_lote_inclui_nao_conformidade_registrada_via_us01():
    dados_nc = {
        "descricao": "Impureza detectada",
        "linha_equipamento": LINHAS_EQUIPAMENTO[0],
        "lote": "LOTE-101",
        "turno": TURNOS[0],
        "responsavel": "João Silva",
    }
    chamar_wsgi("POST", "/api/nao-conformidades", dados_nc)

    resposta = chamar_wsgi("GET", "/api/lotes/LOTE-101")

    corpo = json.loads(resposta["body"])
    assert len(corpo["nao_conformidades"]) == 1
    assert corpo["nao_conformidades"][0]["descricao"] == "Impureza detectada"


def test_metodo_nao_permitido_em_lote_detalhe():
    resposta = chamar_wsgi("POST", "/api/lotes/LOTE-100")

    assert resposta["status"] == "405 Method Not Allowed"
