"""Camada de domínio/armazenamento das não conformidades (em memória)."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from itertools import count
from typing import Dict, List

from .listas_apoio import LINHAS_EQUIPAMENTO, TURNOS

REQUIRED_FIELDS = ("descricao", "linha_equipamento", "lote", "turno", "responsavel")


class ValidationError(Exception):
    """Erro de validação de dados de entrada, com os campos problemáticos."""

    def __init__(self, mensagem: str, campos: List[str] = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campos = campos or []


@dataclass
class NaoConformidade:
    id: int
    descricao: str
    linha_equipamento: str
    lote: str
    turno: str
    responsavel: str
    criado_em: str

    def to_dict(self) -> Dict:
        return asdict(self)


class NaoConformidadeStorage:
    """Armazena não conformidades em memória, sem persistência em disco."""

    def __init__(self):
        self._registros: List[NaoConformidade] = []
        self._id_counter = count(1)

    def limpar(self):
        """Utilizado pelos testes para garantir isolamento entre casos."""
        self._registros.clear()
        self._id_counter = count(1)

    def listar(self) -> List[Dict]:
        return [
            r.to_dict()
            for r in sorted(self._registros, key=lambda r: r.criado_em, reverse=True)
        ]

    def registrar(self, dados: Dict[str, str]) -> Dict:
        campos_faltando = [
            campo for campo in REQUIRED_FIELDS
            if not str(dados.get(campo, "")).strip()
        ]
        if campos_faltando:
            raise ValidationError(
                "Preencha os campos obrigatórios: " + ", ".join(campos_faltando),
                campos_faltando,
            )

        linha = str(dados["linha_equipamento"]).strip()
        turno = str(dados["turno"]).strip()

        if linha not in LINHAS_EQUIPAMENTO:
            raise ValidationError(
                f"Linha/equipamento inválido: {linha}", ["linha_equipamento"]
            )
        if turno not in TURNOS:
            raise ValidationError(f"Turno inválido: {turno}", ["turno"])

        registro = NaoConformidade(
            id=next(self._id_counter),
            descricao=str(dados["descricao"]).strip(),
            linha_equipamento=linha,
            lote=str(dados["lote"]).strip(),
            turno=turno,
            responsavel=str(dados["responsavel"]).strip(),
            criado_em=datetime.now(timezone.utc).isoformat(),
        )
        self._registros.append(registro)
        return registro.to_dict()


# Instância única compartilhada pela aplicação (dados em memória do processo).
storage = NaoConformidadeStorage()
