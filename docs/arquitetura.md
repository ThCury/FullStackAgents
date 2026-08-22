# Arquitetura simples

Esta implementacao usa a arquitetura mais direta possivel para a demo da Trilha B:

```text
Navegador
  |
  | HTML/CSS/JS estatico
  v
Backend HTTP Python
  |
  | regras em memoria
  v
Dados demo Rivexx
```

## Decisoes

- `code/app/frontend`: tela unica responsiva, sem etapa de build.
- `code/app/backend/app.py`: servidor HTTP da biblioteca padrao do Python.
- `code/app/backend/domain.py`: regras de negocio e dados em memoria.
- `code/app/backend/test_domain.py`: testes com `unittest`, sem dependencia externa.
- `code/pipeline`: mantem o squad de agentes do projeto original para demonstrar orquestracao e logs.

## Por que esta arquitetura

- Roda localmente com `python -m backend.app --port 8000`.
- Evita banco de dados, Docker, filas e frameworks para manter a demo pequena.
- Cobre os tres cenarios obrigatorios: registro agil, causa raiz assistida e rastreabilidade de lote.
- Mantem a comunicacao do squad visivel na aba `Squad`, com backlog, decisoes, QA e mensagens.

## Limites assumidos

- Os dados sao reiniciados quando o servidor reinicia.
- A analise de causa usa regras deterministicas simples, nao um modelo de IA em tempo real.
- A rastreabilidade usa lotes semeados para a demo, principalmente `LOTE-4521`.
