"""Health e introspecção da configuração.

`/health/config` existe para o time: mostra em que modo a API está rodando
(fake vs anthropic, memory vs mongo, sandbox). Já economizou tempo de gente
depurando "por que não gastou token" quando o modo era `fake`.

Não expõe segredo: `anthropic_api_key` aparece só como booleano.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from interfaces.http.deps import ContainerDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/config")
async def config(container: ContainerDep) -> dict[str, Any]:
    settings = container.settings
    return {
        "app_name": settings.app_name,
        "llm": settings.llm.value,
        "model": settings.model if settings.llm.value != "fake" else None,
        "api_key_present": bool(settings.anthropic_api_key),
        "persistence": settings.persistence.value,
        "sandbox": settings.sandbox.value,
        "max_rework_cycles": settings.max_rework_cycles,
        "budget": settings.budget_policy().model_dump(),
        "agents": sorted(role.value for role in container.agents),
    }
