from __future__ import annotations

from agents.coder.agent import CoderAgent
from agents.developer.agent import DeveloperAgent
from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from application.project_service import ProjectService
from application.run_service import RunService
from config import BACKEND_CONFIG, AgentLLMProfile, BackendConfig, Settings
from infrastructure.llm import FakeStreamingLLM, GeminiStreamingLLM, OpenAIStreamingLLM
from infrastructure.memory_project_repository import InMemoryProjectRepository
from infrastructure.memory_repository import InMemoryRunRepository
from infrastructure.mongo_project_repository import MongoProjectRepository
from infrastructure.mongo_repository import MongoRunRepository
from infrastructure.workspace_manager import LocalWorkspaceManager, UnavailableWorkspaceManager


class Container:
    def __init__(self, settings: Settings, backend_config: BackendConfig = BACKEND_CONFIG) -> None:
        self.backend_config = backend_config
        repository = self._repository_for(backend_config)
        project_repository = self._project_repository_for(backend_config)

        po_profile = ProductOwnerAgent.llm_profile()
        dev_profile = DeveloperAgent.llm_profile()
        product_owner = ProductOwnerAgent(
            llm=self._llm_for(po_profile, settings),
            model=po_profile.model,
            effort=po_profile.effort,
            max_retries=backend_config.max_llm_retries,
            retry_base_delay_seconds=backend_config.retry_base_delay_seconds,
        )
        developer = DeveloperAgent(
            llm=self._llm_for(dev_profile, settings),
            model=dev_profile.model,
            effort=dev_profile.effort,
            max_iterations=backend_config.max_tool_iterations,
            max_retries=backend_config.max_llm_retries,
            retry_base_delay_seconds=backend_config.retry_base_delay_seconds,
        )
        coder_profile = CoderAgent.llm_profile()
        coder = CoderAgent(
            llm=self._llm_for(coder_profile, settings),
            model=coder_profile.model,
            effort=coder_profile.effort,
            max_iterations=backend_config.max_tool_iterations,
            max_retries=backend_config.max_llm_retries,
            retry_base_delay_seconds=backend_config.retry_base_delay_seconds,
        )
        workspace_manager = (
            LocalWorkspaceManager(settings.dev_workspace_root, backend_config.template_root)
            if settings.dev_workspace_root
            else UnavailableWorkspaceManager()
        )
        calculator = CostCalculator(
            input_price_per_million=backend_config.input_token_price_per_million,
            output_price_per_million=backend_config.output_token_price_per_million,
            price_version=backend_config.price_version,
        )
        self.run_service = RunService(
            repository=repository,
            product_owner=product_owner,
            developer=developer,
            coder=coder,
            workspace_manager=workspace_manager,
            cost_calculator=calculator,
            stream_persist_interval_ms=backend_config.stream_persist_interval_ms,
            project_repository=project_repository,
        )
        self.project_service = ProjectService(project_repository, self.run_service)
        self.repository = repository
        self.project_repository = project_repository
        self.settings = settings

    @staticmethod
    def _repository_for(backend_config: BackendConfig):
        if backend_config.persistence == "mongo":
            return MongoRunRepository(
                backend_config.mongodb_uri,
                backend_config.mongodb_database,
            )
        return InMemoryRunRepository()

    @staticmethod
    def _project_repository_for(backend_config: BackendConfig):
        if backend_config.persistence == "mongo":
            return MongoProjectRepository(
                backend_config.mongodb_uri,
                backend_config.mongodb_database,
            )
        return InMemoryProjectRepository()

    @staticmethod
    def _llm_for(profile: AgentLLMProfile, settings: Settings):
        if profile.provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY é obrigatório para o modelo configurado.")
            return OpenAIStreamingLLM(settings.openai_api_key, profile.model)
        if profile.provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY é obrigatório para o modelo configurado.")
            return GeminiStreamingLLM(settings.gemini_api_key, profile.model)
        return FakeStreamingLLM()
