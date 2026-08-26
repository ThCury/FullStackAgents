from fastapi import APIRouter, Request

from agents.product_owner.agent import ProductOwnerAgent

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    profile = ProductOwnerAgent.llm_profile()
    return {
        "status": "ok",
        "persistence": request.app.state.container.backend_config.persistence,
        "po_llm_provider": profile.provider,
        "po_llm_model": profile.model,
    }
