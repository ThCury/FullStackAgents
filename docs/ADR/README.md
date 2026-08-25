# Architecture Decision Records

ADRs registram decisões estruturais e suas consequências. Uma decisão aceita não
é apagada: se mudar, uma nova ADR substitui a anterior.

| ADR | Decisão | Status |
|---|---|---|
| [0001](0001-monolito-modular-e-portas.md) | Monólito modular com portas e adaptadores | Aceita |
| [0002](0002-langgraph-para-orquestracao.md) | LangGraph para orquestração | Aceita |
| [0003](0003-mongodb-e-auditoria-append-only.md) | MongoDB e histórico append-only | Aceita |
| [0004](0004-contratos-tipados-entre-agentes.md) | Contratos tipados entre agentes | Aceita |
| [0005](0005-medicao-centralizada-de-custos.md) | Medição centralizada de consumo e custos | Aceita |
| [0006](0006-execucao-isolada-do-codigo-gerado.md) | Execução isolada do código gerado | Aceita |
| [0007](0007-copia-isolada-para-projetos-existentes.md) | Cópia isolada para projetos existentes | Aceita |

## Modelo para novas ADRs

```markdown
# ADR-NNNN — Título

**Status:** proposta | aceita | substituída | rejeitada
**Data:** AAAA-MM-DD

## Contexto
## Decisão
## Alternativas consideradas
## Consequências
```
