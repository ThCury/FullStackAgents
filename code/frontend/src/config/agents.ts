/**
 * Agentes do fluxo `fullstack_po_dev_v1`, na ordem em que o grafo do backend
 * os executa. `id` casa com `audit.timeline[].agent.id` e `artifactType`
 * aponta para o artefato que representa a entrega final daquele agente.
 */
export interface AgentDefinition {
  id: string
  role: string
  initial: string
  name: string
  description: string
  /** Posição horizontal do nó no diagrama (viewBox de 900px). */
  x: number
  /** Atraso da animação da partícula no diagrama. */
  delay: string
  artifactType?: string
}

export const AGENTS: AgentDefinition[] = [
  {
    id: 'po',
    role: 'PRODUCT_OWNER',
    initial: 'PO',
    name: 'Product Owner',
    description: 'Interpreta o pedido e escreve o backlog de produto',
    x: 225,
    delay: '0s',
  },
  {
    id: 'dev',
    role: 'DEVELOPER',
    initial: 'DEV',
    name: 'Developer',
    description: 'Lê o código e monta o plano de implementação',
    x: 450,
    delay: '0.3s',
    artifactType: 'development_plan',
  },
  {
    id: 'coder',
    role: 'CODER',
    initial: 'CO',
    name: 'Coder',
    description: 'Escreve o código e reporta o que foi alterado',
    x: 675,
    delay: '0.6s',
    artifactType: 'implementation_report',
  },
]

export const AGENT_BY_ID = new Map(AGENTS.map((agent) => [agent.id, agent]))
