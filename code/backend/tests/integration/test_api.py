"""API HTTP ponta a ponta, incluindo o `lifespan`.

Cuidado que custou tempo: `ASGITransport` **não** dispara o `lifespan`, então o
container nunca é construído e todo endpoint estoura com "container não
inicializado". A entrada explícita em `app.router.lifespan_context` é obrigatória
— e é por isso que este teste existe: ele cobre a montagem real do container, que
os testes do grafo (que montam os nós à mão) não cobrem.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from main import create_app
from tests.conftest import BRIEFING_RIVEXX


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    # Defaults do repo já são fake/memory; fixamos o workspace no tmp para não
    # sujar o diretório do dev ao rodar a suíte.
    monkeypatch.setenv("SQUAD_WORKSPACE_ROOT", str(tmp_path / "ws"))
    monkeypatch.setenv("SQUAD_USE_GIT", "false")

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def _wait_for_terminal(client: AsyncClient, run_id: str, tries: int = 200) -> dict[str, Any]:
    """O run é assíncrono: `POST /runs` devolve 202 e a esteira segue em
    background. Aqui esperamos o estado terminal."""
    for _ in range(tries):
        await asyncio.sleep(0.05)
        run: dict[str, Any] = (await client.get(f"/runs/{run_id}")).json()
        if run["status"] in ("completed", "failed", "awaiting_human"):
            return run
    raise AssertionError("run não atingiu estado terminal no tempo esperado")


async def test_config_expoe_o_modo_sem_vazar_segredo(client: AsyncClient) -> None:
    config = (await client.get("/health/config")).json()

    assert config["llm"] == "fake"
    assert config["persistence"] == "memory"
    assert sorted(config["agents"]) == ["briefing_analyst", "developer", "product_owner", "qa"]
    # A chave nunca aparece — só a existência dela.
    assert "anthropic_api_key" not in config
    assert config["api_key_present"] is False


async def test_ciclo_completo_pela_api(client: AsyncClient) -> None:
    response = await client.post("/runs", json={"briefing": BRIEFING_RIVEXX})
    assert response.status_code == 202, response.text

    run_id = response.json()["id"]
    run = await _wait_for_terminal(client, run_id)
    assert run["status"] == "completed", run.get("failure_reason")

    timeline = (await client.get(f"/runs/{run_id}/timeline")).json()
    assert len(timeline) >= 10
    assert [m["seq"] for m in timeline] == list(range(len(timeline)))

    deliverables = (await client.get(f"/runs/{run_id}/deliverables")).json()
    assert len(deliverables["backlog"]) == 3
    assert deliverables["adrs"]
    assert deliverables["test_reports"]

    metrics = (await client.get(f"/runs/{run_id}/metrics")).json()
    assert metrics["calls_total"] > 0
    assert metrics["budget"]["total_spent"] > 0


async def test_timeline_aceita_delta_e_filtro_por_agente(client: AsyncClient) -> None:
    """`since_seq` é o que permite ao Console reconectar sem recarregar tudo."""
    run_id = (await client.post("/runs", json={"briefing": BRIEFING_RIVEXX})).json()["id"]
    await _wait_for_terminal(client, run_id)

    full = (await client.get(f"/runs/{run_id}/timeline")).json()
    delta = (await client.get(f"/runs/{run_id}/timeline?since_seq={full[2]['seq']}")).json()
    assert len(delta) == len(full) - 3

    only_qa = (await client.get(f"/runs/{run_id}/timeline?agent=qa")).json()
    assert only_qa
    assert {m["from_agent"] for m in only_qa} == {"qa"}


async def test_briefing_curto_e_recusado(client: AsyncClient) -> None:
    response = await client.post("/runs", json={"briefing": "curto"})
    assert response.status_code == 422


async def test_run_inexistente_da_404(client: AsyncClient) -> None:
    assert (await client.get("/runs/run_inexistente")).status_code == 404
