# FullStack Agents

Projeto de um time de agentes capaz de criar aplicações web a partir de um prompt.
O squad mínimo possui Product Owner, Developer e QA, coordenados por LangGraph,
com backend Python e persistência/auditoria em MongoDB.

O DEV pode criar um projeto novo ou evoluir um projeto existente a partir de uma
cópia isolada e auditável.

## Estado atual

O projeto está na fase de definição da arquitetura e dos requisitos. A documentação
é a fonte de verdade para a implementação inicial.

## Documentação

- [Índice da documentação](docs/README.md)
- [Requisitos funcionais e não funcionais](docs/requisitos.md)
- [Arquitetura e princípios SOLID](docs/arquitetura.md)
- [Architecture Decision Records](docs/ADR/README.md)
- [Como executar o backend](docs/instruction.md)

## Resultado esperado do MVP

```text
Prompt do usuário
      ↓
PO cria backlog e critérios
      ↓
DEV implementa uma história
      ↓
QA executa testes ── reprova ──> DEV corrige
      ↓ aprova
Código + instruções + relatório + auditoria de custo
```

Para cada execução será possível consultar prompts, respostas, origem, destino,
modelo, tokens, custo, timeline e artefatos gerados.
