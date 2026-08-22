export type AgentMessage = {
  from_agent: string;
  to_agent: string;
  content: string;
  ts: number;
};

export type DoneSummary = {
  status: string;
  stories: number;
  decisions: number;
  qa_results: { story_id: string; approved: boolean }[];
};

type StreamEvent =
  | { type: "message"; data: AgentMessage }
  | { type: "done"; data: DoneSummary }
  | { type: "error"; data: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Envia a demanda ao backend e consome o stream SSE de resposta, chamando os
 * callbacks conforme os eventos chegam. Usa `fetch` + `ReadableStream` (não
 * `EventSource`) porque a demanda vai no corpo de um POST.
 */
export async function streamDemanda(
  demand: string,
  handlers: {
    onMessage: (message: AgentMessage) => void;
    onDone: (summary: DoneSummary) => void;
    onError: (error: string) => void;
  }
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/demandas/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demand }),
    });
  } catch {
    handlers.onError("Não foi possível conectar ao backend. Ele está rodando?");
    return;
  }

  if (!response.ok || !response.body) {
    handlers.onError(`Backend respondeu com erro (${response.status}).`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const event = JSON.parse(line.slice("data: ".length)) as StreamEvent;
      if (event.type === "message") handlers.onMessage(event.data);
      else if (event.type === "done") handlers.onDone(event.data);
      else handlers.onError(event.data);
    }
  }
}
