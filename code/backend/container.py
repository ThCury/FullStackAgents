from __future__ import annotations

from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from application.run_service import RunService
from config import BACKEND_CONFIG, Settings
from infrastructure.llm import (
    FakeStreamingLLM,
    GeminiStreamingLLM,
    OpenAIStreamingLLM,
)
from infrastructure.memory_repository import InMemoryRunRepository
from infrastructure.mongo_repository import MongoRunRepository


class Container:
    def __init__(self, settings: Settings) -> None:
        if BACKEND_CONFIG.persistence == "mongo":
            repository = MongoRunRepository(
                BACKEND_CONFIG.mongodb_uri,
                BACKEND_CONFIG.mongodb_database,
            )
        else:
            repository = InMemoryRunRepository()

        profile = ProductOwnerAgent.llm_profile()
        if profile.provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY é obrigatório para o modelo do PO.")
            llm = OpenAIStreamingLLM(settings.openai_api_key, profile.model)
        elif profile.provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY é obrigatório para o modelo do PO.")
            llm = GeminiStreamingLLM(settings.gemini_api_key, profile.model)
        else:
            llm = FakeStreamingLLM()

        agent = ProductOwnerAgent(llm=llm, model=profile.model, effort=profile.effort)
        calculator = CostCalculator(
            input_price_per_million=BACKEND_CONFIG.input_token_price_per_million,
            output_price_per_million=BACKEND_CONFIG.output_token_price_per_million,
            price_version=BACKEND_CONFIG.price_version,
        )
        self.run_service = RunService(
            repository=repository,
            agent=agent,
            cost_calculator=calculator,
            stream_persist_interval_ms=BACKEND_CONFIG.stream_persist_interval_ms,
        )
        self.repository = repository
        self.settings = settings
