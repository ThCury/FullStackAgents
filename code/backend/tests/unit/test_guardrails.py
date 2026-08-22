"""Guardas de segurança e orçamento.

Duas coisas que, se falharem em silêncio, viram incidente e não bug:
o workspace aceitando caminho fora da raiz, e o orçamento não sendo aplicado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from domain.entities.delivery import SourceFile
from domain.enums import AgentRole
from domain.errors import BudgetExceeded
from domain.value_objects import BudgetPolicy, TokenUsage
from infrastructure.observability.token_meter import InMemoryTokenMeter
from infrastructure.workspace.local_workspace import LocalGitWorkspace


class TestWorkspaceEscapa:
    """Estamos gravando conteúdo escrito por LLM. Caminho é ataque."""

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> LocalGitWorkspace:
        return LocalGitWorkspace(tmp_path / "ws", use_git=False)

    @pytest.mark.parametrize(
        "path",
        [
            "../fora.py",
            "app/../../fora.py",
            "app/./../../fora.py",
            "/etc/passwd",
            "C:/Windows/System32/x.dll",
        ],
    )
    async def test_recusa_caminho_fora_da_raiz(
        self, workspace: LocalGitWorkspace, path: str
    ) -> None:
        await workspace.prepare("run_1")
        with pytest.raises(ValueError):
            await workspace.write("run_1", [SourceFile(path=path, content="x")])

    async def test_aceita_caminho_relativo_aninhado(self, workspace: LocalGitWorkspace) -> None:
        await workspace.prepare("run_1")
        written = await workspace.write(
            "run_1", [SourceFile(path="app/backend/routers/nc.py", content="# ok")]
        )
        assert written == ["app/backend/routers/nc.py"]
        assert await workspace.read("run_1", "app/backend/routers/nc.py") == "# ok"

    async def test_prepare_limpa_execucao_anterior(self, workspace: LocalGitWorkspace) -> None:
        await workspace.prepare("run_1")
        await workspace.write("run_1", [SourceFile(path="velho.py", content="antigo")])
        await workspace.prepare("run_1")

        with pytest.raises(FileNotFoundError):
            await workspace.read("run_1", "velho.py")


class TestOrcamento:
    async def test_estoura_por_chamada(self) -> None:
        meter = InMemoryTokenMeter(BudgetPolicy(per_run=1000, per_agent=900, per_call=100))

        with pytest.raises(BudgetExceeded) as exc:
            await meter.assert_within_budget("run_1", AgentRole.DEVELOPER, planned=101)
        assert "call" in exc.value.scope

    async def test_estoura_por_agente(self) -> None:
        meter = InMemoryTokenMeter(BudgetPolicy(per_run=10_000, per_agent=150, per_call=100))
        await meter.record("run_1", AgentRole.DEVELOPER, TokenUsage(input_tokens=100))

        with pytest.raises(BudgetExceeded) as exc:
            await meter.assert_within_budget("run_1", AgentRole.DEVELOPER, planned=100)
        assert "agent" in exc.value.scope

    async def test_estoura_por_run(self) -> None:
        meter = InMemoryTokenMeter(BudgetPolicy(per_run=150, per_agent=150, per_call=100))
        await meter.record("run_1", AgentRole.PRODUCT_OWNER, TokenUsage(input_tokens=100))

        with pytest.raises(BudgetExceeded) as exc:
            await meter.assert_within_budget("run_1", AgentRole.DEVELOPER, planned=100)
        assert exc.value.scope == "run"

    async def test_orcamento_e_isolado_por_run(self) -> None:
        """Um run gastão não pode bloquear o próximo."""
        meter = InMemoryTokenMeter(BudgetPolicy(per_run=150, per_agent=150, per_call=100))
        await meter.record("run_1", AgentRole.DEVELOPER, TokenUsage(input_tokens=100))

        await meter.assert_within_budget("run_2", AgentRole.DEVELOPER, planned=100)

    async def test_aprovacao_humana_estende_e_fica_registrada(self) -> None:
        """Estender orçamento é decisão auditável — daí `extensions_approved`."""
        meter = InMemoryTokenMeter(BudgetPolicy(per_run=150, per_agent=150, per_call=100))
        await meter.record("run_1", AgentRole.DEVELOPER, TokenUsage(input_tokens=100))

        with pytest.raises(BudgetExceeded):
            await meter.assert_within_budget("run_1", AgentRole.DEVELOPER, planned=100)

        snapshot = await meter.approve_extension("run_1", 1000)
        assert snapshot.extensions_approved == 1

        await meter.assert_within_budget("run_1", AgentRole.DEVELOPER, planned=100)


class TestCusto:
    def test_soma_de_usage_preserva_todos_os_campos(self) -> None:
        total = TokenUsage(input_tokens=10, output_tokens=5, cache_read_tokens=100) + TokenUsage(
            input_tokens=1, output_tokens=2, cache_write_tokens=7
        )
        assert (total.input_tokens, total.output_tokens) == (11, 7)
        assert (total.cache_read_tokens, total.cache_write_tokens) == (100, 7)

    def test_cache_barateia_a_leitura(self) -> None:
        """Se este teste inverter de sinal, o modelo de custo do painel quebrou."""
        sem_cache = TokenUsage(input_tokens=1_000_000).cost_usd
        com_cache = TokenUsage(cache_read_tokens=1_000_000).cost_usd
        assert com_cache < sem_cache

    def test_politica_incoerente_e_recusada(self) -> None:
        with pytest.raises(ValueError, match="incoerente"):
            BudgetPolicy(per_run=100, per_agent=200, per_call=50)
