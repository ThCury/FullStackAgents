"""Roteadores: funções puras, testadas sem mock.

Este arquivo é o melhor lugar para entender o fluxo do squad — cada teste é uma
regra de negócio de orquestração escrita como asserção.
"""

from __future__ import annotations

from domain.enums import Verdict
from pipeline import routers
from pipeline.state import SquadState


def _state(**overrides: object) -> SquadState:
    base: SquadState = {
        "run_id": "run_1",
        "current_story_id": "story_1",
        "test_reports": [],
        "rework": {},
        "escalations": [],
        "queue": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


class TestAfterDispatch:
    def test_com_story_vai_para_o_dev(self) -> None:
        assert routers.after_dispatch(_state()) == "developer"

    def test_sem_story_integra(self) -> None:
        assert routers.after_dispatch(_state(current_story_id=None)) == "integrate"


class TestAfterQa:
    def test_aprovada_segue_para_proxima_story(self) -> None:
        state = _state(test_reports=[{"story_ref": "story_1", "verdict": Verdict.APPROVED.value}])
        assert routers.after_qa(state, max_rework=3) == "dispatch"

    def test_reprovada_volta_para_o_dev(self) -> None:
        state = _state(
            test_reports=[{"story_ref": "story_1", "verdict": Verdict.REJECTED.value}],
            rework={"story_1": 1},
        )
        assert routers.after_qa(state, max_rework=3) == "developer"

    def test_reprovada_no_limite_escala(self) -> None:
        """É o que impede loop infinito Dev<->QA queimando orçamento."""
        state = _state(
            test_reports=[{"story_ref": "story_1", "verdict": Verdict.REJECTED.value}],
            rework={"story_1": 3},
        )
        assert routers.after_qa(state, max_rework=3) == "escalate"

    def test_sem_relatorio_escala_em_vez_de_aprovar(self) -> None:
        """QA que não produziu relatório é falha de execução, não aprovação.

        Aprovar por omissão seria o pior comportamento possível aqui.
        """
        assert routers.after_qa(_state(), max_rework=3) == "escalate"

    def test_usa_o_relatorio_mais_recente_da_story(self) -> None:
        state = _state(
            test_reports=[
                {"story_ref": "story_1", "verdict": Verdict.REJECTED.value},
                {"story_ref": "story_1", "verdict": Verdict.APPROVED.value},
            ],
            rework={"story_1": 1},
        )
        assert routers.after_qa(state, max_rework=3) == "dispatch"

    def test_ignora_relatorio_de_outra_story(self) -> None:
        state = _state(test_reports=[{"story_ref": "story_9", "verdict": Verdict.APPROVED.value}])
        assert routers.after_qa(state, max_rework=3) == "escalate"


class TestAfterEscalate:
    def test_retry_devolve_ao_dev(self) -> None:
        state = _state(escalations=[{"resolution": "retry"}])
        assert routers.after_escalate(state) == "developer"

    def test_finish_encerra_o_run(self) -> None:
        state = _state(escalations=[{"resolution": "finish"}])
        assert routers.after_escalate(state) == "integrate"

    def test_skip_segue_o_backlog(self) -> None:
        state = _state(escalations=[{"resolution": "skip"}])
        assert routers.after_escalate(state) == "dispatch"

    def test_sem_decisao_trata_como_skip(self) -> None:
        assert routers.after_escalate(_state()) == "dispatch"
