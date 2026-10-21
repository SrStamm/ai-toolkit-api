import type { AgentQuestion } from "@/types/agent";

interface IngestFileResponse {
  status: string;
  job_id: string;
}

export const uploadAndIngestFile = async (
  file: File,
  domain: string,
  topic: string,
): Promise<IngestFileResponse> => {
  const baseUrl = import.meta.env.VITE_URL || "";
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source", file.name);
  formData.append("domain", domain);
  formData.append("topic", topic);

  const response = await fetch(`${baseUrl}/rag/ingest-file/job`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Ingest failed: ${response.statusText}`);
  }

  return response.json() as Promise<IngestFileResponse>;
};

interface AgentAskOptions {
  provider?: string;
  model?: string;
  useStream?: boolean;
  signal?: AbortSignal;
}

export const agentAskStream = (
  body: AgentQuestion,
  options: AgentAskOptions = {},
  onEvent: (eventName: string, data: Record<string, unknown>) => void,
  onError?: (error: string) => void,
  onEnd?: () => void,
): void => {
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
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

  // Fires once when the SSE reader finishes normally. It is not called on
  // abort (client cancellation) nor when the read fails — those paths report
  // through `onError`.
  const notifyEnd = () => {
    if (!onEnd) return;
    try {
      onEnd();
    } catch (err) {
      console.error("End-of-stream handler failed:", err);
    }
  };

  fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(body),
    signal: options.signal,
  })
    .then(async (response) => {
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

      await readStream();

      // The reader finished normally: the stream ended without a read error.
      // Aborts and read failures reject before reaching this point, so the
      // end-of-stream callback only fires for a clean end of stream.
      notifyEnd();
    })
    .catch((err) => {
      // AbortError is expected when user cancels — don't propagate as error
      if (err instanceof DOMException && err.name === "AbortError") return;
      const errorMessage = err instanceof Error ? err.message : "Stream error";
      if (onError) onError(errorMessage);
    });
};
