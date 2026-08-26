# Requisitos do produto

## 1. Objetivo

Receber uma descrição em linguagem natural e coordenar um time de agentes para
planejar, implementar e testar uma aplicação web. O sistema funciona tanto para
criar um projeto novo quanto para evoluir um projeto existente. Deve permitir que
uma pessoa entenda, depois da execução, quem pediu o quê, quem respondeu, quanto
foi consumido e quais artefatos foram produzidos.

## 2. Atores

| Ator | Responsabilidade |
|---|---|
| Usuário | Envia o prompt, acompanha a execução e consulta os resultados. |
| PO Agent | Converte o prompt em escopo, histórias e critérios de aceite. |
| DEV Agent | Implementa as histórias e registra decisões técnicas. |
| QA Agent | Valida critérios, executa testes e aprova ou solicita correção. |
| Orquestrador | Controla estados, limites, handoffs, retries e encerramento. |
| Administrador | Configura modelos, preços, limites e política de retenção. |

## 3. Requisitos funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF-001 | Criar um `run` a partir de um prompt e do modo `new_project` ou `existing_project`. | Must |
| RF-002 | Gerar um identificador único e manter o status do `run`. | Must |
| RF-003 | O PO deve produzir backlog priorizado e critérios verificáveis. | Must |
| RF-004 | O DEV deve receber uma história por vez e alterar apenas o workspace do `run`. | Must |
| RF-005 | O QA deve relacionar critérios de aceite a testes e registrar evidências. | Must |
| RF-006 | Uma reprovação do QA deve voltar ao DEV com os problemas encontrados. | Must |
| RF-007 | O sistema deve encerrar ou pedir intervenção ao atingir o limite de correções. | Must |
| RF-008 | O sistema deve armazenar cada prompt e cada resposta de modelo sem truncamento silencioso. | Must |
| RF-009 | Cada chamada deve informar remetente, destinatário, modelo, duração, tokens e custo. | Must |
| RF-010 | Todo handoff deve registrar origem, destino, resumo, artefatos e correlação. | Must |
| RF-011 | O usuário deve consultar timeline, chamadas, custos e artefatos de um `run`. | Must |
| RF-012 | O custo deve ser agregado por chamada, agente, modelo e `run`. | Must |
| RF-013 | O sistema deve interromper novas chamadas ao exceder orçamento configurado. | Must |
| RF-014 | Falhas transitórias devem admitir retry sem duplicar eventos de negócio. | Should |
| RF-015 | Uma execução interrompida deve poder continuar de um checkpoint. | Should |
| RF-016 | Prompts de sistema dos agentes devem ser versionados. | Should |
| RF-017 | O resultado deve conter código, instruções de execução e relatório de QA. | Must |
| RF-018 | O administrador deve configurar tabela de preços por provedor/modelo e vigência. | Should |
| RF-019 | No modo `new_project`, o DEV deve criar o projeto a partir de um scaffold aprovado ou de uma estrutura vazia configurada. | Must |
| RF-020 | No modo `existing_project`, o sistema deve receber uma referência autorizada do projeto e criar uma cópia de trabalho isolada. | Must |
| RF-021 | Antes de alterar projeto existente, o DEV deve registrar diagnóstico: tecnologias, comandos, testes, arquivos relevantes e estado do Git. | Must |
| RF-022 | A entrega de projeto existente deve conter diff, arquivos alterados, comandos executados e instruções de aplicação/reversão. | Must |
| RF-023 | O administrador deve configurar uma raiz local autorizada para os workspaces do DEV. | Must |
| RF-024 | Projetos novos devem partir de um template versionado, identificado no artefato da run. | Must |
| RF-025 | Cada projeto gerado deve incluir comandos documentados para compilar, testar e executar via Docker Compose. | Must |

## 4. Regras de negócio

- RN-001: nenhum artefato pode ser considerado aprovado sem veredito do QA.
- RN-002: o QA não aprova somente pela resposta do LLM; deve anexar evidência de
  execução automatizada ou justificar explicitamente uma verificação manual.
- RN-003: cada chamada de LLM pertence a exatamente um `run` e um agente.
- RN-004: o valor cobrado pelo provedor, quando disponível, prevalece sobre a
  estimativa calculada pela tabela de preços.
- RN-005: a tabela e a versão de preço usadas no cálculo devem ficar registradas.
- RN-006: eventos de auditoria são acrescentados; correções geram novos eventos em
  vez de alterar o histórico.
- RN-007: o limite de tentativas e o orçamento são definidos antes da execução;
  qualquer extensão deve gerar um evento de decisão humana.
- RN-008: o código gerado nunca é executado no processo da API.
- RN-009: o repositório de origem é somente leitura durante um `run`; apenas a
  cópia de trabalho isolada pode ser modificada.
- RN-010: o sistema não faz `push`, merge ou deploy em projeto existente sem ação
  explícita e autenticada do usuário fora do fluxo automático do MVP.
- RN-011: um diagnóstico de projeto existente não pode expor segredos encontrados
  em arquivos de configuração; eles devem ser mascarados antes de virar contexto.
- RN-012: toda operação de escrita do DEV deve ter caminho final resolvido abaixo
  da raiz de workspace autorizada; o agente não recebe acesso ao restante do disco.
- RN-013: uma run de projeto novo deve registrar a versão exata do template de que
  foi derivada e as evidências de build e teste.

## 5. Requisitos não funcionais

| ID | Requisito | Critério inicial do MVP |
|---|---|---|
| RNF-001 | Auditabilidade | 100% das chamadas e handoffs possuem `run_id`, `correlation_id`, `timestamp` UTC e `brasil_datetime` em `America/Sao_Paulo`. |
| RNF-002 | Segurança | Segredos não entram em prompts, logs ou respostas persistidas; dados sensíveis podem ser mascarados. |
| RNF-003 | Isolamento | Código gerado executa em processo/container separado, sem credenciais da API. |
| RNF-004 | Confiabilidade | Eventos usam chave de idempotência; retries não duplicam a contabilização. |
| RNF-005 | Desempenho | Criação do `run` responde em até 2 s e inicia trabalho assíncrono. |
| RNF-006 | Escalabilidade | API sem estado local; estado durável e checkpoints ficam fora do processo. |
| RNF-007 | Observabilidade | Logs estruturados incluem `run_id`, `agent`, `node`, latência e resultado. |
| RNF-008 | Manutenibilidade | Domínio não importa LangGraph, MongoDB, framework web ou SDK de LLM. |
| RNF-009 | Testabilidade | Casos de uso aceitam adaptadores fake/in-memory em testes. |
| RNF-010 | Privacidade | Retenção e acesso a prompts/respostas são configuráveis e protegidos por autorização. |
| RNF-011 | Recuperação | Checkpoint permite retomar sem repetir nós já concluídos. |
| RNF-012 | Portabilidade | Desenvolvimento e testes executam localmente por configuração documentada. |

## 6. Critérios de aceite do MVP

1. Dado um prompt válido, o sistema cria um `run` e o PO gera ao menos uma história
   com critérios de aceite.
2. O DEV produz arquivos no workspace exclusivo do `run`.
3. O QA executa testes e aprova, ou devolve uma lista objetiva ao DEV.
4. Em uma reprovação, a timeline mostra o ciclo completo e o número da tentativa.
5. Ao concluir, código, backlog, decisões e relatório de QA ficam consultáveis.
6. Para qualquer chamada é possível ver origem, destino, prompt, resposta, tokens
   de entrada/saída, modelo, latência e custo.
7. A soma das chamadas coincide com os totais por agente e por `run`.
8. Ao exceder o orçamento, nenhuma chamada adicional é realizada sem autorização.
9. Cada evento exibido ao usuário mostra `brasil_datetime`; o mesmo registro
   preserva seu `timestamp` UTC para ordenação e integração.
10. Dado um repositório existente autorizado, o sistema preserva a origem, cria
    uma cópia isolada e entrega um diff auditável sem alterar a branch original.
11. Dado um projeto novo, o sistema cria o workspace abaixo da raiz autorizada,
    copia o template versionado e entrega comandos Docker Compose para executá-lo.

## 7. Matriz de rastreabilidade

| Capacidade | Requisitos | Componente principal |
|---|---|---|
| Orquestração | RF-001 a RF-007, RF-014, RF-015 | `RunSquad`, grafo e checkpoints |
| Auditoria | RF-008 a RF-012, RF-016, RF-018 | `AuditRecorder`, `CostCalculator` |
| Entrega | RF-017, RF-019 a RF-022, RN-001, RN-002 | agentes, workspace e executor |
| Segurança | RN-007, RN-008, RNF-002, RNF-003, RNF-010 | políticas e sandbox |
