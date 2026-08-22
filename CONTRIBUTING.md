# Como trabalhar neste repositório

Leia antes do primeiro PR. É curto, e cada regra aqui existe porque a alternativa custa caro.

---

## A regra de dependência

As setas de dependência apontam **sempre para dentro**:

```
interfaces/  ─┐
infrastructure/ ─┤
pipeline/    ─┼──►  application/  ──►  domain/
factory/     ─┘                        (não importa nada)
agents/      ─────►  domain/
```

`domain/`, `application/` e `agents/` **não conhecem framework nenhum**. Nem FastAPI, nem Mongo, nem LangGraph, nem o SDK da Anthropic.

Isso não é convenção de code review — **é regra de lint**. O `ruff` tem a lista de imports banidos por camada (`TID251` no `pyproject.toml`), e quebrar derruba o CI.

**Se você precisa de um import banido em uma camada interna, a dependência está invertida.** O caminho é:

1. Declare uma *port* (`Protocol`) em `domain/ports/`
2. Implemente em `infrastructure/`
3. Ligue em `factory/container.py`

Exemplo real: o QA Agent precisa executar testes. Ele não importa `subprocess` — ele recebe `TestRunnerPort`. Consequência prática: dá para rodar todo o QA com um runner falso, e o agente literalmente **não consegue** executar comando arbitrário, porque não tem a port para isso.

## Injete o mínimo

Ao dar dependências a um agente, dê só o que o papel precisa. Se você se pegar querendo passar "tudo", provavelmente o agente está fazendo duas coisas.

A segregação de interface aqui é **controle de escopo do agente**, não higiene de código. O Dev Agent tem `CodeWorkspacePort`; o QA não. O QA tem `TestRunnerPort`; o Dev não.

---

## Adicionando um agente

Três lugares, e **nenhum agente existente é editado** (é o OCP na prática):

1. `agents/<papel>.py` — herde de `BaseAgent`, declare `role`, `output_model`, `to_agent`
2. `agents/prompts/<papel>.md` — o system prompt
3. `agents/schemas.py` — o schema de saída (um `Draft`)

Depois ligue:

4. `factory/container.py` → `_build_agents()`
5. `pipeline/nodes/` → um nó adapter
6. `pipeline/graph.py` → o nó e suas arestas
7. `infrastructure/llm/fixtures.py` → a resposta canônica, para o modo `fake` continuar funcionando

### Herde de `BaseAgent`, sempre

`BaseAgent.run()` é um *template method* que garante a emissão da `AgentMessage` auditável. Isso não é opcional: o enunciado da trilha diz que "um output final sem orquestração visível não será considerado". Se cada agente fosse responsável por lembrar de emitir o handoff, um esquecimento em review custaria a nota.

Você implementa os hooks (`build_prompt`, `summarize`, `explain`, `validate`, `reference`). A persistência e a publicação do evento não são sua responsabilidade — e você não tem acesso ao repositório para fazê-las de outro jeito.

### Escreva o `validate()`

Schema garante **forma**. `validate()` garante **suficiência** — e é onde mora o modo de falha mais insidioso deste projeto: um agente que devolve algo bem formado mas insuficiente.

Exemplos reais no código:

- PO que não cobriu um dos 3 cenários obrigatórios
- QA que deixou um critério de aceite sem caso de teste
- QA que aprovou com um caso falhando
- Dev que registrou ADR sem alternativa real considerada
- Analyst que começou a escrever requisito (invadindo o papel do PO)

Falhar no `validate()` custa uma chamada. Descobrir no `integrate` custa o run inteiro.

---

## Onde a regra de negócio mora

| Tipo de regra | Lugar |
|---|---|
| Contrato de papel ("o PO precisa cobrir os 3 cenários") | `agents/<papel>.py` → `validate()` |
| Fluxo do squad ("QA reprovou 3x → escala") | `pipeline/routers.py` |
| Invariante de dado ("reprovação exige `required_changes`") | `domain/entities/` → validator pydantic |
| Orquestração de ports ("cria run, dispara grafo") | `application/use_cases/` |
| **Nunca** | `pipeline/nodes/` |

Um nó é um adapter fino: traduz estado ↔ agente e nada mais. Se você está escrevendo um `if` sobre conteúdo de domínio dentro de um nó, ele pertence a uma das linhas acima.

---

## Nós determinísticos por default

`dispatch`, `escalate` e `integrate` são código comum, sem LLM. Isso é deliberado: escolher a próxima story, pausar para um humano e montar o relatório final são decisões com regra conhecida. Delegar a um modelo custaria dinheiro para introduzir variabilidade onde não queremos nenhuma.

**Se a regra é conhecida, o nó é determinístico.** Um agente só entra quando o trabalho é interpretação, geração ou julgamento.

---

## Coleções append-only

`agent_messages`, `llm_calls`, `artifacts`, `adrs`, `test_reports`.

Os repositórios delas só têm `append`. **Não adicione `update` nem `delete`** — a imutabilidade é o que faz a trilha ser auditoria em vez de log. Retrabalho gera nova tentativa; as anteriores ficam, e é assim que o Console mostra a evolução após uma reprovação.

No estado do grafo isso é garantido pela estrutura: os campos append-only usam o reducer `operator.add`, então é *impossível* um nó sobrescrever o histórico.

---

## Prompt caching: não quebre o prefixo

O `system` prompt é o prefixo estável e cacheável. **Nada volátil pode entrar nele** — nem timestamp, nem id de run, nem contador. Um `datetime.now()` ali invalida o cache silenciosamente e o custo triplica sem ninguém perceber.

É por isso que os prompts vivem em `.md` e não em f-string: fica óbvio que não há interpolação.

Como verificar: o Inspector do Console mostra o `prompt_hash`. Se ele muda entre chamadas do mesmo agente, o cache está quebrado. O painel de métricas mostra `cache_hit_rate` — se cair para zero, algum prefixo virou volátil.

---

## Custo: ajuste `effort`, não o modelo

Todos os agentes usam `claude-opus-5` (ADR-05). Para economizar, baixe `output_config.effort` em `factory/settings.py` → `agent_profiles()`. Não troque de modelo — a capacidade importa mais em codegen do que a economia.

Meça antes de calibrar: o painel de tokens do Console mostra custo por agente.

---

## Testes

```bash
cd code/backend && .venv/Scripts/python -m pytest
```

Regras da suíte:

- **Nenhum teste toca rede, Mongo ou Docker.** `FakeLLM` + repositórios em memória + `FrozenClock` + `SequentialIdGenerator`. Um run inteiro é reproduzível, o que permite asseverar a trilha de auditoria por igualdade exata.
- `tests/integration/test_squad_end_to_end.py` é o smoke test que importa. Se ele passa, a esteira funciona.
- Ao mudar um schema de agente, atualize a fixture correspondente. `test_fixtures_batem_com_os_schemas` falha primeiro e aponta a causa — sem ele, o modo `fake` quebraria e a suíte mentiria sobre o motivo.

O `FakeLLM` **reprova a primeira avaliação do QA de propósito**. Não é bug: o caminho felizão nunca exercitaria a aresta condicional `qa → developer`, que é a parte interessante do grafo.

---

## Antes de abrir PR

```bash
make check
```

Lint, format, mypy `strict` e testes no backend; typecheck e build no frontend. Mesmo gate do CI.

### Decisões arquiteturais

Mudança que altere uma decisão de [docs/arquitetura.md](docs/arquitetura.md) precisa de ADR nova em `docs/adr/`. Use o formato dos ADRs existentes — em especial, **alternativas consideradas de verdade**. Se você não consegue nomear uma alternativa plausível, a decisão provavelmente é trivial e não precisa de ADR.

É a mesma exigência que fazemos ao Dev Agent. Vale para nós também.
