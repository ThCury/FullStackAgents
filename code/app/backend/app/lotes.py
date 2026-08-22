"""Dados de apoio e lógica de rastreabilidade de lotes (US-02).

Os lotes são dados de apoio pré-carregados (seed), em memória, representando
o histórico de produção. A partir de um código de lote é possível recuperar
seus dados de produção e a lista de "lotes correlatos".
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class Lote:
    codigo: str
    materia_prima: str
    fornecedor: str
    equipamento: str
    turno: str
    operadores: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


# Dados de apoio pré-carregados (seed). LOTE-100 e LOTE-101 compartilham a
# mesma matéria-prima/fornecedor; LOTE-100 e LOTE-102 compartilham o mesmo
# equipamento e turno - garantindo casos de lotes correlatos para demonstração.
LOTES_SEED: List[Dict] = [
    {
        "codigo": "LOTE-100",
        "materia_prima": "Farinha de Trigo Tipo 1",
        "fornecedor": "Moinho Central",
        "equipamento": "Linha 1 - Envase",
        "turno": "1º Turno",
        "operadores": ["João Silva", "Maria Souza"],
    },
    {
        "codigo": "LOTE-101",
        "materia_prima": "Farinha de Trigo Tipo 1",
        "fornecedor": "Moinho Central",
        "equipamento": "Linha 2 - Envase",
        "turno": "2º Turno",
        "operadores": ["Carlos Pereira"],
    },
    {
        "codigo": "LOTE-102",
        "materia_prima": "Açúcar Refinado",
        "fornecedor": "Usina Doce Vale",
        "equipamento": "Linha 1 - Envase",
        "turno": "1º Turno",
        "operadores": ["Ana Lima", "João Silva"],
    },
]


class LoteStorage:
    """Armazena os lotes de apoio em memória e resolve rastreabilidade."""

    def __init__(self, lotes: Optional[List[Dict]] = None):
        dados = lotes if lotes is not None else LOTES_SEED
        self._lotes: List[Lote] = [Lote(**dado) for dado in dados]

    def listar(self) -> List[Dict]:
        return [lote.to_dict() for lote in self._lotes]

    def buscar(self, codigo: str) -> Optional[Lote]:
        if not codigo or not str(codigo).strip():
            return None
        codigo_normalizado = str(codigo).strip().lower()
        for lote in self._lotes:
            if lote.codigo.lower() == codigo_normalizado:
                return lote
        return None

    def correlatos(self, lote: Lote) -> List[Lote]:
        """Lotes que compartilham a mesma matéria-prima OU o mesmo
        equipamento e turno do lote informado, excluindo ele próprio."""
        resultado = []
        for outro in self._lotes:
            if outro.codigo == lote.codigo:
                continue
            mesma_materia_prima = outro.materia_prima == lote.materia_prima
            mesmo_equipamento_e_turno = (
                outro.equipamento == lote.equipamento and outro.turno == lote.turno
            )
            if mesma_materia_prima or mesmo_equipamento_e_turno:
                resultado.append(outro)
        return resultado


# Instância única compartilhada pela aplicação.
lote_storage = LoteStorage()


def consultar_lote(codigo: str, nao_conformidades: List[Dict]) -> Optional[Dict]:
    """Monta a resposta completa de rastreabilidade de um lote: dados do
    lote, lotes correlatos e não conformidades associadas. Retorna None se
    o lote não existir nos dados de apoio."""
    lote = lote_storage.buscar(codigo)
    if lote is None:
        return None

    correlatos = lote_storage.correlatos(lote)
    nao_conformidades_do_lote = [
        nc for nc in nao_conformidades
        if str(nc.get("lote", "")).strip().lower() == lote.codigo.lower()
    ]

    return {
        "lote": lote.to_dict(),
        "correlatos": [correlato.to_dict() for correlato in correlatos],
        "nao_conformidades": nao_conformidades_do_lote,
    }
