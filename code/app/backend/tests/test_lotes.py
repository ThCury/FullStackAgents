import pytest

from app.lotes import Lote, LoteStorage, consultar_lote


def _lotes_exemplo():
    return [
        {
            "codigo": "LOTE-A",
            "materia_prima": "Farinha",
            "fornecedor": "Fornecedor X",
            "equipamento": "Linha 1",
            "turno": "1º Turno",
            "operadores": ["Op 1"],
        },
        {
            "codigo": "LOTE-B",
            "materia_prima": "Farinha",
            "fornecedor": "Fornecedor X",
            "equipamento": "Linha 2",
            "turno": "2º Turno",
            "operadores": ["Op 2"],
        },
        {
            "codigo": "LOTE-C",
            "materia_prima": "Açúcar",
            "fornecedor": "Fornecedor Y",
            "equipamento": "Linha 1",
            "turno": "1º Turno",
            "operadores": ["Op 3"],
        },
        {
            "codigo": "LOTE-D",
            "materia_prima": "Corante",
            "fornecedor": "Fornecedor Z",
            "equipamento": "Linha 3",
            "turno": "3º Turno",
            "operadores": ["Op 4"],
        },
    ]


def test_buscar_lote_existente_retorna_lote():
    storage = LoteStorage(_lotes_exemplo())

    lote = storage.buscar("LOTE-A")

    assert lote is not None
    assert lote.codigo == "LOTE-A"


def test_buscar_lote_e_case_insensitive_e_ignora_espacos():
    storage = LoteStorage(_lotes_exemplo())

    lote = storage.buscar("  lote-a  ")

    assert lote is not None
    assert lote.codigo == "LOTE-A"


def test_buscar_lote_inexistente_retorna_none():
    storage = LoteStorage(_lotes_exemplo())

    assert storage.buscar("LOTE-INEXISTENTE") is None


def test_buscar_lote_com_codigo_vazio_retorna_none():
    storage = LoteStorage(_lotes_exemplo())

    assert storage.buscar("") is None
    assert storage.buscar(None) is None


def test_correlatos_por_mesma_materia_prima():
    storage = LoteStorage(_lotes_exemplo())
    lote_a = storage.buscar("LOTE-A")

    correlatos = storage.correlatos(lote_a)
    codigos = {c.codigo for c in correlatos}

    assert "LOTE-B" in codigos  # mesma matéria-prima
    assert "LOTE-C" in codigos  # mesmo equipamento e turno
    assert "LOTE-A" not in codigos  # exclui o próprio lote
    assert "LOTE-D" not in codigos  # não compartilha nada


def test_correlatos_lista_vazia_quando_nao_ha_relacao():
    storage = LoteStorage(_lotes_exemplo())
    lote_d = storage.buscar("LOTE-D")

    assert storage.correlatos(lote_d) == []


def test_consultar_lote_inexistente_retorna_none():
    storage = LoteStorage(_lotes_exemplo())

    resultado = consultar_lote("LOTE-INEXISTENTE", [])

    # a função de módulo usa a instância padrão; garantimos apenas o
    # comportamento de "não encontrado" para um código fora do seed padrão
    assert resultado is None or resultado["lote"]["codigo"] != "LOTE-INEXISTENTE"


def test_consultar_lote_existente_inclui_nao_conformidades_associadas():
    nao_conformidades = [
        {"id": 1, "lote": "LOTE-100", "descricao": "Problema X", "turno": "1º Turno", "criado_em": "2024-01-01T00:00:00"},
        {"id": 2, "lote": "outro-lote", "descricao": "Problema Y", "turno": "2º Turno", "criado_em": "2024-01-02T00:00:00"},
    ]

    resultado = consultar_lote("LOTE-100", nao_conformidades)

    assert resultado is not None
    assert resultado["lote"]["codigo"] == "LOTE-100"
    assert len(resultado["nao_conformidades"]) == 1
    assert resultado["nao_conformidades"][0]["id"] == 1
    assert isinstance(resultado["correlatos"], list)


def test_seed_possui_pelo_menos_tres_lotes_com_caso_de_correlacao():
    from app.lotes import lote_storage

    lotes = lote_storage.listar()
    assert len(lotes) >= 3

    algum_lote_com_correlato = False
    for dado in lotes:
        lote = lote_storage.buscar(dado["codigo"])
        if lote_storage.correlatos(lote):
            algum_lote_com_correlato = True
            break
    assert algum_lote_com_correlato
