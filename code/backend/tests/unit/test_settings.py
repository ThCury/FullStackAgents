"""Configuração — os defaults que fazem o projeto rodar no dia zero.

Cada teste aqui corresponde a um problema que apareceu de verdade ao subir o
projeto pela primeira vez. Config errada não quebra em teste unitário nenhum:
ela quebra no primeiro clique de quem clonou o repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.settings import DEFAULT_WORKSPACE_ROOT, LlmMode, PersistenceMode, Settings


class TestDefaultsDoDiaZero:
    def test_roda_sem_chave_e_sem_banco(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clonar e rodar não pode exigir API key nem Mongo."""
        monkeypatch.delenv("SQUAD_LLM", raising=False)
        monkeypatch.delenv("SQUAD_PERSISTENCE", raising=False)

        settings = Settings(_env_file=None)

        assert settings.llm is LlmMode.FAKE
        assert settings.persistence is PersistenceMode.MEMORY


class TestWorkspaceRoot:
    def test_default_fica_fora_do_diretorio_vigiado_pelo_reload(self) -> None:
        """O `uvicorn --reload` vigia `code/backend`.

        Se o workspace do código gerado ficasse lá dentro, cada arquivo escrito
        pelo Dev Agent reiniciaria o servidor e mataria o run no meio. Os
        excludes default do uvicorn não salvam: eles casam com o nome do
        arquivo, e `nc_form.py` não começa com ponto.
        """
        backend_dir = Path(__file__).resolve().parents[2]

        assert not DEFAULT_WORKSPACE_ROOT.is_relative_to(backend_dir), (
            f"{DEFAULT_WORKSPACE_ROOT} está dentro de {backend_dir} — "
            "o --reload vai matar todo run em andamento"
        )

    def test_default_e_absoluto(self) -> None:
        """Caminho derivado do módulo, não do CWD.

        Assim `uvicorn`, `pytest` e um script solto resolvem para a mesma pasta.
        Um caminho relativo faria cada um criar o seu.
        """
        assert DEFAULT_WORKSPACE_ROOT.is_absolute()


class TestApiKey:
    def test_le_a_variavel_padrao_sem_prefixo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A variável é `ANTHROPIC_API_KEY`, não `SQUAD_ANTHROPIC_API_KEY`.

        Sem o `validation_alias`, o campo ficava sempre vazio: `/health/config`
        reportava `api_key_present: false` com a chave configurada, e o modo
        `anthropic` morria por credencial faltando.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste")

        settings = Settings(_env_file=None)

        assert settings.anthropic_api_key == "sk-ant-teste"

    def test_prefixo_squad_nao_e_usado_para_a_chave(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("SQUAD_ANTHROPIC_API_KEY", "nao-deveria-ser-lida")

        settings = Settings(_env_file=None)

        assert settings.anthropic_api_key is None


class TestOrcamentoEEffort:
    def test_todo_papel_de_ia_tem_perfil(self) -> None:
        """Papel sem perfil cairia no default silenciosamente, e o dial de custo
        do ADR-05 deixaria de valer para ele."""
        from domain.enums import AgentRole

        profiles = Settings(_env_file=None).agent_profiles()
        papeis_de_ia = {
            AgentRole.BRIEFING_ANALYST,
            AgentRole.PRODUCT_OWNER,
            AgentRole.DEVELOPER,
            AgentRole.QA,
        }

        assert set(profiles) == papeis_de_ia

    def test_dev_recebe_o_maior_effort(self) -> None:
        """Codegen é a tarefa mais sensível a capacidade (ADR-05)."""
        from domain.enums import AgentRole, Effort

        profiles = Settings(_env_file=None).agent_profiles()
        ordem = [Effort.LOW, Effort.MEDIUM, Effort.HIGH, Effort.XHIGH, Effort.MAX]
        dev = profiles[AgentRole.DEVELOPER].effort

        assert ordem.index(dev) >= max(
            ordem.index(p.effort) for r, p in profiles.items() if r is not AgentRole.DEVELOPER
        )

    def test_politica_de_orcamento_e_coerente(self) -> None:
        policy = Settings(_env_file=None).budget_policy()

        assert policy.per_call <= policy.per_agent <= policy.per_run
