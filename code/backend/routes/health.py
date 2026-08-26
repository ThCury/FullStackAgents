from fastapi import APIRouter

from agents.product_owner.agent import ProductOwnerAgent
from config import BACKEND_CONFIG

router = APIRouter()


@router.get("/health")
def health() -> dict:
    profile = ProductOwnerAgent.llm_profile()
    return {
        "status": "ok",
        "persistence": BACKEND_CONFIG.persistence,
        "po_llm_provider": profile.provider,
        "po_llm_model": profile.model,
    }

