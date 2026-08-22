# ADR-0009 — Pydantic é permitido no `domain/`

**Status:** aceita
**Data:** 2026-08-22
**Contexto da decisão:** implementação inicial da arquitetura

## Contexto

A §6 de `docs/arquitetura.md` foi escrita dizendo que `domain/` teria "ZERO imports de framework". Na implementação, as entidades e value objects ficaram em `pydantic.BaseModel`, não em `dataclasses` da stdlib.

Este ADR registra o desvio explicitamente, em vez de deixar a doc e o código se contradizendo em silêncio.

A força que criou a tensão: as entidades do domínio atravessam três fronteiras em todo run — LLM (structured output), Mongo (documento) e HTTP/SSE (JSON para o Console). Com stdlib pura, cada travessia exige mapeamento manual.

## Decisão

`domain/` depende da stdlib **e do Pydantic**, e de nada mais. Nenhum outro pacote externo é permitido ali — FastAPI, Motor, LangGraph e o SDK da Anthropic seguem barrados por lint (`TID251`).

O critério que aplicamos: Pydantic é biblioteca de **modelagem de dados**, não framework de aplicação. Ela não impõe ciclo de vida, não faz I/O, não decide fluxo. Trocá-la seria trabalhoso, mas não mudaria o desenho das camadas — o que é o teste prático de "isso é detalhe de infraestrutura?".

## Alternativas consideradas

- **`dataclasses` no domínio + mappers em `infrastructure/persistence/`.** Purismo correto e o que a doc dizia. Custo: ~7 mappers bidirecionais só para as entidades atuais, mais um para cada schema de agente. Times afogam em mappers e eles apodrecem — o mapper esquecido é um bug silencioso de campo faltando, exatamente a classe de erro que a validação deveria pegar.
- **`attrs` + `cattrs`.** Mesma dependência externa que Pydantic, com menos integração: perderíamos `model_json_schema()` (que alimenta o structured output direto do schema do agente) e o suporte nativo do FastAPI.
- **Duas hierarquias — entidade pura no domínio, DTO Pydantic na borda.** Duplica cada modelo. Na prática as duas hierarquias divergem, e a de domínio vira a que ninguém atualiza.
- **`TypedDict` em vez de classes.** Sem validação em runtime. Perderíamos os invariantes que hoje são validators (`TestReport` exigindo `required_changes` na reprovação, `BudgetPolicy` recusando teto incoerente) — e esses invariantes são justamente a defesa contra o agente devolver algo bem formado mas inválido.

## Justificativa

Pydantic paga em quatro lugares de uma vez neste projeto:

1. `model_json_schema()` gera o JSON Schema do structured output direto do schema do agente. Não existe segunda definição para sair de sincronia.
2. `model_dump(mode="json")` serializa para Mongo, SSE e HTTP sem mapper.
3. `model_validate` na leitura valida o que veio do banco — trilha de auditoria não deveria confiar em documento cru.
4. Os validators concentram invariantes de domínio onde eles pertencem, no tipo, em vez de espalhados em `if` pelos casos de uso.

Nenhuma das alternativas entrega os quatro. O purismo com mappers entrega zero e cobra manutenção.

## Consequências

**Mais fácil:** atravessar as fronteiras sem boilerplate; um invariante novo é um validator, não um `if` em três lugares; o schema do agente e o do LLM não podem divergir.

**Mais difícil:** trocar de biblioteca de modelagem exigiria mexer em `domain/` — não é grátis, embora não mude o desenho das camadas. Um `frozen=True` esquecido deixa uma entidade mutável passar, então frozen é obrigatório em value object (e o `Frozen` base em `value_objects.py` existe para isso).

**Risco a vigiar:** a linha "biblioteca de dados vs framework" é a que sustenta esta decisão. Se alguém começar a usar recurso de Pydantic que faz I/O ou controla ciclo de vida dentro de `domain/`, a justificativa cai e o ADR precisa ser revisto.
