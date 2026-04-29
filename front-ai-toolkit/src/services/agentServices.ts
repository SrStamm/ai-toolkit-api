import type { AgentQuestion, AgentResponse } from "@/types/agent";
import Fetch from "@/utils/api";

interface AgentAskOptions {
  provider?: string;
  model?: string;
  useStream?: boolean;
}

export const agentAsk = async (body: AgentQuestion, options: AgentAskOptions = {}): Promise<AgentResponse> => {
  const headers: Record<string, string> = {};

  if (options.provider) {
    headers["x-llm-provider"] = options.provider;
  }
  if (options.model) {
    headers["x-llm-model"] = options.model;
  }

  return await Fetch<AgentResponse>({
    path: "/agent/agent-loop",
    method: "POST",
    body: body,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
  });
};

export const agentAskStream = (
  body: AgentQuestion,
  options: AgentAskOptions = {},
  onEvent: (event: string, data: any) => void,
  onError?: (error: string) => void,
): void => {
  const headers: Record<string, string> = {
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
  };

  if (options.provider) {
    headers["x-llm-provider"] = options.provider;
  }
  if (options.model) {
    headers["x-llm-model"] = options.model;
  }

  const baseUrl = import.meta.env.VITE_URL || "";
  const url = `${baseUrl}/agent/agent-loop/stream`;

  fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(body),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      const readStream = async () => {
        if (!reader) return;

        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process all complete events (event + data pairs)
          const events = buffer.split("\n\n");
          buffer = events.pop() || ""; // Keep incomplete event in buffer

          for (const eventBlock of events) {
            if (!eventBlock.trim()) continue;

            const lines = eventBlock.split("\n");
            let eventName = "";
            let dataStr = "";

            for (const line of lines) {
              const trimmed = line.trim();
              if (trimmed.startsWith("event:")) {
                eventName = trimmed.substring(6).trim();
              } else if (trimmed.startsWith("data:")) {
                dataStr = trimmed.substring(5).trim();
              }
            }

            if (eventName && dataStr) {
              try {
                const data = JSON.parse(dataStr);
                onEvent(eventName, data);
              } catch (err) {
                console.error("Failed to parse SSE data:", dataStr, err);
              }
            }
          }
        }

        // Process any remaining buffer
        if (buffer.trim()) {
          const lines = buffer.split("\n");
          let eventName = "";
          let dataStr = "";
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("event:")) {
              eventName = trimmed.substring(6).trim();
            } else if (trimmed.startsWith("data:")) {
              dataStr = trimmed.substring(5).trim();
            }
          }
          if (eventName && dataStr) {
            try {
              const data = JSON.parse(dataStr);
              onEvent(eventName, data);
            } catch (err) {
              console.error("Failed to parse final SSE data:", dataStr, err);
            }
          }
        }
      };

      return readStream();
    })
    .catch((err) => {
      const errorMessage = err instanceof Error ? err.message : "Stream error";
      if (onError) onError(errorMessage);
    });
};