# Pipeline de agentes (LangGraph)

Squad autônomo de 4 agentes que recebe um briefing de cliente e entrega
funcionalidades implementadas em `code/app`, sem intervenção humana entre o
recebimento do brief e a entrega final.

## Fluxo

```
START -> Analyst -> PO -> Dev -> QA --(reprovado, ainda há retentativas)--> Dev
                                  \--(aprovado ou retentativas esgotadas)--> advance
                     advance --(há próxima story)--> Dev
                     advance --(backlog concluído)--> END
```

- **Analyst** (`agents/analyst_agent.py`): recebe o brief bruto, explora o
  estado atual de `code/app` (leitura apenas) e produz um brief técnico
  enriquecido com contexto de negócio, escopo delimitado e riscos.
- **PO** (`agents/po_agent.py`): único agente que conhece o brief original.
  Quebra o brief enriquecido em user stories priorizadas com critérios de
  aceite testáveis. Persiste o backlog em `artifacts/backlog.json`.
- **Dev** (`agents/dev_agent.py`): implementa uma story por vez em
  `code/app` (leitura/escrita), escreve testes unitários e só entrega quando
  a suíte de testes passa. Registra cada decisão técnica com justificativa em
  `artifacts/decision_log.jsonl`.
- **QA** (`agents/qa_agent.py`): faz code review contra os critérios de
  aceite da story, roda os testes (integração) e reprova com feedback
  específico quando algo não bate. Só o que for aprovado avança. Relatório em
  `artifacts/qa_report.jsonl`.

Toda comunicação entre agentes é registrada em
`artifacts/runs/<NNN>_<timestamp>/communication_log.jsonl` (quem falou com
quem, e o quê) — é isso que torna a orquestração auditável.

## Brief inicial vs. incremento

O primeiro brief recebido constrói a aplicação em `code/app` do zero. Cada
execução seguinte é tratada como um **incremento** sobre o que já foi
entregue - não é preciso sinalizar isso explicitamente.

Isso funciona porque cada chamada a `run_pipeline` grava sua própria pasta em
`artifacts/runs/<NNN>_<timestamp>/` (brief recebido, backlog, decisões, QA,
comunicação) e o Analyst recebe, além do código atual de `code/app`, um resumo
textual de todas as execuções anteriores (`history.py`). Com isso ele
consegue diferenciar "construir do zero" de "adicionar/alterar algo que já
existe", e instrui o PO a não recriar stories de escopo já entregue.

## Modo interativo

```bash
python3 -m pipeline.run --interactive
```

Pede um brief por vez no terminal (finalize cada mensagem com uma linha em
branco). A primeira mensagem constrói o sistema; as próximas incrementam o
que já foi construído, uma de cada vez.

## Isolamento de responsabilidades

- `agents/`: cada classe é responsável pela própria construção (modelo,
  system prompt, tools). O pipeline nunca monta prompts ou lida com a API do
  LLM diretamente.
- `graph.py`: só instancia as classes de `agents/` e registra `agent.run`
  como nó do grafo. A única lógica própria do pipeline é o roteamento entre
  nós (retrabalho vs. avanço vs. fim).
- `tools/`: ferramentas de arquivo (travadas dentro de `code/app`) e de
  execução de testes, compartilhadas pelos agentes que precisam delas.

## Como rodar

```bash
cd code/pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha ANTHROPIC_API_KEY
cd ..                  # execute a partir de code/, para o import `pipeline.*` funcionar
python3 -m pipeline.run --brief-file pipeline/briefs/rivexx.txt
```

O resultado final (status, stories, decisões, veredito do QA) é impresso no
final da execução, e o detalhe completo de cada rodada fica em
`pipeline/artifacts/runs/<NNN>_<timestamp>/`.

## Uso programático

```python
from pipeline.run import run_pipeline

result = run_pipeline(brief_text, max_revisions=2)
result["backlog"]           # user stories geradas pelo PO
result["decision_log"]      # decisões técnicas do Dev
result["qa_report"]         # veredito do QA por story
result["communication_log"] # comunicação completa entre os agentes
```
