"""Respostas canônicas do `FakeLLM` para o briefing da Rivexx.

Para que servem
---------------
1. **Rodar o squad sem API key.** Um dev novo clona, sobe e vê a orquestração
   funcionando em segundos. Isso é o que destrava o trabalho em paralelo: quem
   está no Console não fica bloqueado por quem está nos prompts.
2. **Teste determinístico.** O grafo, os roteadores, o retrabalho e a auditoria
   têm cobertura sem tocar em rede.
3. **Fallback de demo.** Se a API cair na apresentação, `SQUAD_LLM=fake` entrega
   a esteira inteira funcionando.

Estes dados NÃO são o entregável — são andaime. Ao ligar `SQUAD_LLM=anthropic`,
o agente real produz o conteúdo de verdade. Mantenha as fixtures válidas contra
os schemas de `agents/schemas.py`; o teste `test_fixtures_match_schemas` falha se
divergirem.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# BriefingAnalyst
# ---------------------------------------------------------------------------
BRIEFING_ANALYST: dict[str, Any] = {
    "company": "Rivexx Componentes",
    "context": (
        "Indústria de componentes plásticos de alta precisão, 2 plantas, fornecimento "
        "para os setores automotivo e eletroeletrônico. Certificada, auditada "
        "trimestralmente, 480 colaboradores, operação em 3 turnos."
    ),
    "pains": [
        {
            "statement": "Investigação de não conformidade é manual e leva horas",
            "verbatim": (
                "Toda não conformidade detectada — internamente ou pelo cliente — "
                "desencadeia uma investigação manual."
            ),
            "impact": "Horas de retrabalho por ocorrência",
        },
        {
            "statement": "Informação de produção dispersa entre papel, planilha e memória",
            "verbatim": (
                "A informação existe, mas está espalhada em registros físicos, "
                "planilhas e memória de pessoas."
            ),
            "impact": "Reconstituição de histórico não é confiável nem auditável",
        },
        {
            "statement": "Causa raiz é definida por opinião, sem método estruturado",
            "verbatim": "A causa raiz vira opinião.",
            "impact": "Recorrência do mesmo defeito",
        },
        {
            "statement": "Plano de ação não é monitorado após criação",
            "verbatim": "O plano de ação vira promessa sem monitoramento.",
            "impact": "Ação corretiva sem verificação de eficácia",
        },
        {
            "statement": "Impossível responder rapidamente quais lotes foram afetados",
            "verbatim": (
                "quando um cliente aciona a Rivexx por um defeito, ninguém consegue "
                "responder rapidamente quais lotes foram afetados e onde estão."
            ),
            "impact": "Exposição em recall e perda de confiança do cliente",
        },
    ],
    "constraints": [
        {
            "kind": "non_functional",
            "statement": "Aplicação responsiva, uso primário em celular no chão de fábrica",
            "verbatim": "Aplicação responsiva — operadores registram pelo celular no chão de fábrica",
        },
        {
            "kind": "non_functional",
            "statement": "Interface operável sem treinamento técnico",
            "verbatim": "Interface operável sem treinamento técnico",
        },
        {
            "kind": "compliance",
            "statement": "Todo registro precisa de data, responsável, turno e equipamento",
            "verbatim": "Todo registro com evidência auditável — data, responsável, turno e equipamento",
        },
        {
            "kind": "functional",
            "statement": "Rastreabilidade de lote cobrindo toda a cadeia produtiva",
            "verbatim": "Rastreabilidade de lote cobrindo toda a cadeia produtiva",
        },
    ],
    "actors": [
        {
            "name": "Operador",
            "responsibility": "Registra a não conformidade na linha, pelo celular",
        },
        {
            "name": "Coordenador de Qualidade",
            "responsibility": "Conduz a análise de causa raiz e rastreia lotes",
        },
        {
            "name": "Responsável pela ação",
            "responsibility": "Executa e comprova o plano de ação corretiva",
        },
        {"name": "Auditor", "responsibility": "Verifica a trilha de evidências trimestralmente"},
    ],
    "glossary": [
        {
            "term": "Não conformidade (NC)",
            "definition": "Desvio de especificação detectado interna ou externamente",
        },
        {
            "term": "Lote",
            "definition": "Unidade rastreável de produção, do insumo recebido ao produto expedido",
        },
        {"term": "Turno", "definition": "Um dos 3 períodos de operação diária"},
        {
            "term": "Causa raiz",
            "definition": "Origem confirmada do desvio, apurada por metodologia estruturada",
        },
        {
            "term": "Genealogia de lote",
            "definition": "Cadeia de ascendência e descendência entre lotes",
        },
        {
            "term": "Plano de ação corretiva",
            "definition": "Conjunto de ações com responsável, prazo e verificação de eficácia",
        },
    ],
    "open_questions": [
        {
            "question": "Qual o volume mensal de não conformidades e de lotes por planta?",
            "why_it_matters": "Define estratégia de índice e paginação na rastreabilidade",
            "blocks_scenarios": ["rastreabilidade_de_lote"],
        },
        {
            "question": "Existe ERP/MES de onde vêm os dados de lote, ou o registro é manual?",
            "why_it_matters": "Determina se há integração ou cadastro na própria aplicação",
            "blocks_scenarios": ["rastreabilidade_de_lote"],
        },
        {
            "question": "Quais perfis de acesso existem e o que cada um pode ver ou editar?",
            "why_it_matters": "Registro auditável exige identidade; sem perfis não há responsável confiável",
            "blocks_scenarios": ["registro_agil", "causa_raiz_assistida"],
        },
        {
            "question": "Qual o prazo legal de retenção dos registros de qualidade?",
            "why_it_matters": "Afeta política de retenção e imutabilidade da trilha",
            "blocks_scenarios": [],
        },
        {
            "question": "O chão de fábrica tem conectividade estável ou é preciso operação offline?",
            "why_it_matters": "Operação offline muda a arquitetura do frontend por completo",
            "blocks_scenarios": ["registro_agil"],
        },
    ],
    "methodology_refs": [
        {
            "name": "5 Porquês",
            "applies_to": "Análise de causa raiz de defeito pontual",
            "summary": "Encadeamento iterativo de perguntas até a causa sistêmica",
        },
        {
            "name": "Diagrama de Ishikawa (6M)",
            "applies_to": "Análise de causa raiz com múltiplas categorias de causa",
            "summary": "Classifica causas em Método, Máquina, Mão de obra, Material, Medição e Meio ambiente",
        },
        {
            "name": "8D",
            "applies_to": "Tratamento de reclamação de cliente",
            "summary": "Oito disciplinas, da contenção à prevenção de recorrência",
        },
        {
            "name": "5W2H",
            "applies_to": "Estruturação de plano de ação corretiva",
            "summary": "O quê, por quê, onde, quando, quem, como e quanto custa",
        },
    ],
}

# ---------------------------------------------------------------------------
# Product Owner
# ---------------------------------------------------------------------------
PRODUCT_OWNER: dict[str, Any] = {
    "problem_interpretation": (
        "O problema da Rivexx não é falta de dado, é falta de ligação entre dados. "
        "Cada NC, lote, turno e equipamento existe em algum registro, mas em suportes "
        "que não se cruzam — daí as horas de investigação e a causa raiz por opinião. "
        "A aplicação precisa ser o lugar onde esses vínculos são criados no momento do "
        "registro, para depois serem percorridos em segundos. Priorizo o registro ágil "
        "primeiro, porque sem dado de entrada confiável nem a causa raiz nem a "
        "rastreabilidade têm o que consultar."
    ),
    "stories": [
        {
            "title": "Registrar não conformidade pelo celular na linha de produção",
            "narrative": (
                "Como Operador, quero registrar uma não conformidade pelo celular em "
                "menos de um minuto, para que o desvio seja capturado sem interromper a linha."
            ),
            "priority": "must",
            "scenario_tag": "registro_agil",
            "acceptance_criteria": [
                {
                    "given": "que estou autenticado como operador em um celular",
                    "when": "abro o formulário de registro de não conformidade",
                    "then": "vejo os campos de tipo, descrição, linha e lote em uma única tela, sem rolagem horizontal",
                },
                {
                    "given": "que preenchi tipo, descrição, linha 4 e o código do lote",
                    "when": "envio o registro",
                    "then": "o registro é salvo com data, responsável, turno e equipamento preenchidos automaticamente",
                },
                {
                    "given": "que deixei a descrição do defeito em branco",
                    "when": "tento enviar o registro",
                    "then": "vejo uma mensagem indicando o campo obrigatório e nada é salvo",
                },
                {
                    "given": "que informei um código de lote inexistente",
                    "when": "envio o registro",
                    "then": "vejo um aviso de lote não encontrado e o registro não é salvo",
                },
            ],
            "depends_on_titles": [],
            "rationale": (
                "Must porque é a porta de entrada de todo o resto: sem registro estruturado, "
                "causa raiz e rastreabilidade não têm dado para operar."
            ),
        },
        {
            "title": "Conduzir análise de causa raiz com sugestão baseada em histórico",
            "narrative": (
                "Como Coordenador de Qualidade, quero conduzir a análise de causa raiz "
                "com método estruturado e ver causas sugeridas a partir de NCs "
                "semelhantes, para que a conclusão deixe de ser opinião."
            ),
            "priority": "must",
            "scenario_tag": "causa_raiz_assistida",
            "acceptance_criteria": [
                {
                    "given": "que existe uma não conformidade registrada",
                    "when": "abro a análise de causa raiz dessa NC",
                    "then": "vejo a estrutura dos 5 Porquês e as causas sugeridas a partir de NCs históricas do mesmo equipamento ou tipo de defeito",
                },
                {
                    "given": "que confirmei a causa raiz da análise",
                    "when": "solicito a geração do plano de ação",
                    "then": "um plano em 5W2H é criado com responsável, prazo e status inicial pendente",
                },
                {
                    "given": "que existe um plano de ação com prazo vencido",
                    "when": "acesso a lista de planos de ação",
                    "then": "o plano aparece sinalizado como atrasado",
                },
            ],
            "depends_on_titles": ["Registrar não conformidade pelo celular na linha de produção"],
            "rationale": (
                "Must porque é o que ataca as duas dores centrais — causa raiz por opinião e "
                "plano sem monitoramento. Depende do registro existir."
            ),
        },
        {
            "title": "Rastrear a cadeia produtiva completa de um lote",
            "narrative": (
                "Como Coordenador de Qualidade, quero informar um código de lote e ver "
                "toda a cadeia em segundos, para responder ao cliente quais lotes foram "
                "afetados e onde estão."
            ),
            "priority": "must",
            "scenario_tag": "rastreabilidade_de_lote",
            "acceptance_criteria": [
                {
                    "given": "que informo o código de um lote de produto acabado",
                    "when": "consulto a rastreabilidade",
                    "then": "vejo matéria-prima, fornecedor, equipamento, turno e operadores que participaram da cadeia",
                },
                {
                    "given": "que estou vendo a rastreabilidade de um lote",
                    "when": "consulto os lotes correlatos",
                    "then": "vejo os lotes que compartilham a mesma matéria-prima ou o mesmo equipamento no mesmo turno",
                },
                {
                    "given": "que informo um código de lote que não existe",
                    "when": "consulto a rastreabilidade",
                    "then": "vejo uma mensagem de lote não encontrado, sem erro de aplicação",
                },
            ],
            "depends_on_titles": [],
            "rationale": (
                "Must e independente do registro: é o cenário de maior exposição comercial "
                "(acionamento por cliente) e pode ser desenvolvido em paralelo."
            ),
        },
    ],
    "out_of_scope": [
        "Integração com ERP/MES — sem contrato definido no briefing (pergunta aberta do Analyst)",
        "Operação offline no chão de fábrica — assumo conectividade estável até confirmação",
        "Gestão de perfis e permissões além de operador e coordenador",
        "Emissão de relatório regulatório para o órgão auditor",
    ],
}


# ---------------------------------------------------------------------------
# Developer — resposta genérica, parametrizada pela story
# ---------------------------------------------------------------------------
def developer_output(story_title: str, slug: str, rework: bool = False) -> dict[str, Any]:
    """Andaime: um artefato plausível e válido contra `DeveloperOutput`.

    Não pretende ser o código real da Rivexx — com `SQUAD_LLM=anthropic` o Dev
    Agent escreve o de verdade. Aqui só precisa ter forma correta para o grafo,
    o QA e a auditoria rodarem ponta a ponta.
    """
    suffix = "\n# revisao apos reprovacao do QA\n" if rework else "\n"
    return {
        "files": [
            {
                "path": f"app/backend/routers/{slug}.py",
                "content": (
                    f'"""Endpoints de {story_title}."""\n'
                    "from fastapi import APIRouter\n\n"
                    f"router = APIRouter(prefix='/{slug}', tags=['{slug}'])\n"
                    f"{suffix}"
                ),
                "kind": "source_code",
            },
            {
                "path": f"app/frontend/src/pages/{slug}.tsx",
                "content": (
                    f"// Tela responsiva de {story_title}\n"
                    f"export default function Page() {{ return <main>{slug}</main> }}\n"
                ),
                "kind": "source_code",
            },
            {
                "path": f"app/backend/tests/test_{slug}.py",
                "content": ("def test_placeholder() -> None:\n    assert True\n"),
                "kind": "test_code",
            },
        ],
        "adrs": [
            {
                "title": f"Modelagem de dados para {story_title}",
                "context": (
                    "A story exige evidência auditável (data, responsável, turno, equipamento) "
                    "em todo registro, e consulta por lote precisa ser rápida."
                ),
                "decision": (
                    "Documento único por registro com os campos de evidência embutidos, "
                    "mais coleção separada e append-only para a trilha de auditoria."
                ),
                "alternatives_considered": [
                    "Trilha de auditoria como array dentro do próprio documento — cresce sem limite e complica o índice",
                    "Tabelas normalizadas em banco relacional — travessia de genealogia exigiria CTE recursiva",
                    "Event sourcing completo — reconstrução de estado custa mais do que o cenário exige",
                ],
                "rationale": (
                    "Documento embutido atende a leitura dominante (abrir uma NC) em uma query, "
                    "e a trilha separada preserva imutabilidade sem inflar o documento principal."
                ),
                "consequences": (
                    "Mais fácil: leitura e evolução de schema. Mais difícil: consulta agregada "
                    "sobre a trilha, que passa a exigir pipeline de agregação."
                ),
            }
        ],
        "implementation_notes": (
            f"Implementação de '{story_title}' seguindo o contrato do scaffold: "
            "router no backend, página responsiva no frontend, teste de API."
        ),
        "how_to_verify": (
            f"Suba o app e chame GET /{slug}. No frontend, abra /{slug} em viewport de 375px "
            f"e confirme ausência de rolagem horizontal. Rode `pytest app/backend/tests/test_{slug}.py`."
        ),
    }


# ---------------------------------------------------------------------------
# QA — resposta parametrizada pelos critérios da story
# ---------------------------------------------------------------------------
def qa_output(criteria_ids: list[str], approve: bool) -> dict[str, Any]:
    """Gera um caso por critério — a cobertura que o `QaAgent.validate` exige."""
    if approve:
        return {
            "verdict": "approved",
            "cases": [
                {
                    "criterion_ref": cid,
                    "title": f"Verificação do critério {cid}",
                    "steps": [
                        "Subir a aplicação no sandbox",
                        "Executar a suíte de API e a suíte de UI",
                        "Conferir o resultado observável descrito no critério",
                    ],
                    "expected": "Comportamento descrito no critério de aceite",
                    "outcome": "passed",
                    "actual": "Comportamento observado conforme o esperado na execução da suíte",
                    "duration_ms": 120,
                }
                for cid in criteria_ids
            ],
            "summary": (
                f"{len(criteria_ids)} critério(s) exercitado(s) por execução real da suíte. "
                "Todos os casos passaram."
            ),
            "rejection_reason": None,
            "required_changes": [],
        }

    # Primeira passada reprova, para exercitar o ciclo de retrabalho Dev<->QA.
    first, rest = criteria_ids[0], criteria_ids[1:]
    return {
        "verdict": "rejected",
        "cases": [
            {
                "criterion_ref": first,
                "title": f"Verificação do critério {first}",
                "steps": ["Subir a aplicação", "Submeter o formulário sem o campo obrigatório"],
                "expected": "Mensagem de campo obrigatório e nada salvo",
                "outcome": "failed",
                "actual": "Registro foi salvo com o campo vazio; nenhuma validação disparou",
                "duration_ms": 95,
            },
            *[
                {
                    "criterion_ref": cid,
                    "title": f"Verificação do critério {cid}",
                    "steps": ["Subir a aplicação", "Exercitar o critério"],
                    "expected": "Comportamento descrito no critério",
                    "outcome": "passed",
                    "actual": "Comportamento observado conforme o esperado",
                    "duration_ms": 110,
                }
                for cid in rest
            ],
        ],
        "summary": "1 caso reprovado na execução. Entrega devolvida ao Dev Agent.",
        "rejection_reason": "Validação de campo obrigatório ausente no backend",
        "required_changes": [
            "Validar campo obrigatório de descrição no schema do backend e retornar 422 com a mensagem do campo",
            "Exibir a mensagem de erro no formulário do frontend sem perder o que o operador já digitou",
        ],
    }
