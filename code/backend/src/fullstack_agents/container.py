from __future__ import annotations

from fullstack_agents.agents.product_owner.agent import ProductOwnerAgent
from fullstack_agents.application.costs import CostCalculator
from fullstack_agents.application.run_service import RunService
from fullstack_agents.config import Settings
from fullstack_agents.infrastructure.llm import FakeStreamingLLM, OpenAIStreamingLLM
from fullstack_agents.infrastructure.memory_repository import InMemoryRunRepository
from fullstack_agents.infrastructure.mongo_repository import MongoRunRepository


class Container:
    def __init__(self, settings: Settings) -> None:
        if settings.persistence == "mongo":
            repository = MongoRunRepository(settings.mongodb_uri, settings.mongodb_database)
        else:
            repository = InMemoryRunRepository()

        if settings.llm_mode == "openai":
            if not settings.openai_api_key or not settings.openai_model:
                raise ValueError("OPENAI_API_KEY e OPENAI_MODEL são obrigatórios no modo openai.")
            llm = OpenAIStreamingLLM(settings.openai_api_key, settings.openai_model)
            model = settings.openai_model
        else:
            llm = FakeStreamingLLM()
            model = llm.model

        agent = ProductOwnerAgent(llm=llm, model=model, effort=settings.openai_effort)
        calculator = CostCalculator(
            input_price_per_million=settings.input_token_price_per_million,
            output_price_per_million=settings.output_token_price_per_million,
            price_version=settings.price_version,
        )
        self.run_service = RunService(
            repository=repository,
            agent=agent,
            cost_calculator=calculator,
            stream_persist_interval_ms=settings.stream_persist_interval_ms,
        )
        self.repository = repository
        self.settings = settings

