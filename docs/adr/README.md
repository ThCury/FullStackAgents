# Architecture Decision Records

As decisões estruturais estão consolidadas em [../arquitetura.md](../arquitetura.md) §2 (ADR-01 a ADR-09). Este diretório recebe as **novas** decisões, uma por arquivo, a partir daqui.

## Quando escrever uma ADR

Quando a mudança altera uma decisão registrada na arquitetura, ou introduz uma escolha estrutural nova: modelagem de dados, contrato entre camadas, novo agente, troca de biblioteca de infraestrutura, mudança na ordem do template method do `BaseAgent`.

Não escreva ADR para: nome de variável, refactor local, correção de bug, ajuste de prompt sem mudança de papel.

## Formato

Copie `0010-template.md`. O campo que costuma ser feito mal é **alternativas consideradas**:

> Alternativas reais, que você de fato pesou. "Não fazer nada" e "fazer diferente" não são alternativas. Se você não consegue nomear uma alternativa plausível, a decisão provavelmente é trivial e não precisa de ADR.

É exatamente a exigência que o `DeveloperAgent.validate()` faz ao Dev Agent (`alternatives_considered` com `min_length=1`). Vale para nós também — seria estranho cobrar do agente o que não cobramos de nós.

## Numeração

Continue de onde a arquitetura parou: a próxima é `0010`. Os números 0001–0009 estão em `arquitetura.md` §2.

| # | Decisão | Onde |
|---|---|---|
| 0001 | MongoDB como persistência do squad | arquitetura.md §2 |
| 0002 | Não usar Cassandra | arquitetura.md §2 |
| 0003 | LangGraph `StateGraph` para orquestração | arquitetura.md §2 |
| 0004 | `$graphLookup` para genealogia de lote | arquitetura.md §2 |
| 0005 | `claude-opus-5` para todos os agentes; `effort` como dial de custo | arquitetura.md §2 |
| 0006 | Dev Agent gera código real em disco, versionado | arquitetura.md §2 |
| 0007 | `BriefingAnalyst` pré-PO normaliza, não interpreta | arquitetura.md §2 e §5.1 |
| 0008 | Código gerado executa em sandbox isolado | arquitetura.md §2 |
| 0009 | Pydantic é permitido no `domain/` | [0009-pydantic-no-dominio.md](0009-pydantic-no-dominio.md) |
