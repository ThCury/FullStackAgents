"""Vocabulário fechado do domínio.

Todo enum aqui é parte do contrato entre agentes. Adicionar um valor é decisão
de arquitetura — registre uma ADR em `docs/adr/`.
"""

from enum import StrEnum


class AgentRole(StrEnum):
    """Papéis do squad. Um papel = uma responsabilidade (SRP)."""

    BRIEFING_ANALYST = "briefing_analyst"
    PRODUCT_OWNER = "product_owner"
    DEVELOPER = "developer"
    QA = "qa"
    ORCHESTRATOR = "orchestrator"  # nós determinísticos (dispatch, integrate)
    HUMAN = "human"  # decisões vindas do `interrupt()`


class MessageKind(StrEnum):
    """Natureza de um handoff entre agentes.

    É o que permite ao Console filtrar a timeline e ao avaliador enxergar o
    squad *decidindo*, não só produzindo.
    """

    HANDOFF = "handoff"  # passei o bastão
    DELIVERY = "delivery"  # entreguei um artefato
    REJECTION = "rejection"  # reprovei o que recebi
    QUESTION = "question"  # preciso de input para seguir
    DECISION = "decision"  # decidi algo e registrei o porquê


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


class Priority(StrEnum):
    """MoSCoW — o PO Agent é obrigado a priorizar, não só listar."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class StoryStatus(StrEnum):
    BACKLOG = "backlog"
    IN_DEVELOPMENT = "in_development"
    IN_QA = "in_qa"
    REWORK = "rework"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class Verdict(StrEnum):
    """Veredito do QA. `only libera o que estiver validado`."""

    APPROVED = "approved"
    REJECTED = "rejected"


class TestOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScenarioTag(StrEnum):
    """Os 3 cenários obrigatórios da demo (Trilha B).

    Serve de checklist: o `integrate` falha se algum cenário não tiver story
    aceita.
    """

    QUICK_REGISTRATION = "registro_agil"
    ASSISTED_ROOT_CAUSE = "causa_raiz_assistida"
    LOT_TRACEABILITY = "rastreabilidade_de_lote"


class Effort(StrEnum):
    """Dial de custo/qualidade por agente (`output_config.effort`).

    Preferimos baixar o effort a trocar de modelo — ver ADR-05.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


class ArtifactKind(StrEnum):
    SOURCE_CODE = "source_code"
    TEST_CODE = "test_code"
    MIGRATION = "migration"
    DOCUMENTATION = "documentation"
