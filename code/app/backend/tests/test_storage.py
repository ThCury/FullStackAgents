import pytest

from app.listas_apoio import LINHAS_EQUIPAMENTO, TURNOS
from app.storage import ValidationError, storage

DADOS_VALIDOS = {
    "descricao": "Vazamento de óleo na esteira",
    "linha_equipamento": LINHAS_EQUIPAMENTO[0],
    "lote": "LOTE-123",
    "turno": TURNOS[0],
    "responsavel": "João Silva",
}


def test_registrar_com_dados_validos_retorna_registro_com_id_e_data():
    registro = storage.registrar(DADOS_VALIDOS)

    assert registro["id"] is not None
    assert registro["descricao"] == DADOS_VALIDOS["descricao"]
    assert registro["linha_equipamento"] == DADOS_VALIDOS["linha_equipamento"]
    assert registro["lote"] == DADOS_VALIDOS["lote"]
    assert registro["turno"] == DADOS_VALIDOS["turno"]
    assert registro["responsavel"] == DADOS_VALIDOS["responsavel"]
    assert registro["criado_em"]  # preenchido automaticamente


def test_registrar_adiciona_na_listagem():
    storage.registrar(DADOS_VALIDOS)

    registros = storage.listar()

    assert len(registros) == 1
    assert registros[0]["descricao"] == DADOS_VALIDOS["descricao"]


def test_listagem_ordenada_por_criacao_mais_recente_primeiro():
    primeiro = storage.registrar(DADOS_VALIDOS)
    segundo = storage.registrar({**DADOS_VALIDOS, "descricao": "Segundo defeito"})

    registros = storage.listar()

    assert registros[0]["id"] == segundo["id"]
    assert registros[1]["id"] == primeiro["id"]


@pytest.mark.parametrize("campo_ausente", [
    "descricao", "linha_equipamento", "lote", "turno", "responsavel",
])
def test_registrar_sem_campo_obrigatorio_lanca_erro_com_campo_indicado(campo_ausente):
    dados = dict(DADOS_VALIDOS)
    dados[campo_ausente] = "   "

    with pytest.raises(ValidationError) as excecao:
        storage.registrar(dados)

    assert campo_ausente in excecao.value.campos
    assert storage.listar() == []


def test_registrar_com_multiplos_campos_vazios_lista_todos():
    dados = dict(DADOS_VALIDOS)
    dados["descricao"] = ""
    dados["lote"] = ""

    with pytest.raises(ValidationError) as excecao:
        storage.registrar(dados)

    assert set(excecao.value.campos) == {"descricao", "lote"}


def test_registrar_com_linha_fora_da_lista_de_apoio_lanca_erro():
    dados = dict(DADOS_VALIDOS)
    dados["linha_equipamento"] = "Linha Inexistente"

    with pytest.raises(ValidationError) as excecao:
        storage.registrar(dados)

    assert "linha_equipamento" in excecao.value.campos


def test_registrar_com_turno_invalido_lanca_erro():
    dados = dict(DADOS_VALIDOS)
    dados["turno"] = "4º Turno"

    with pytest.raises(ValidationError) as excecao:
        storage.registrar(dados)

    assert "turno" in excecao.value.campos
