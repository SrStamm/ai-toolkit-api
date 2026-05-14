import { useState, useCallback } from "react";
import { agentAskStream, uploadAgentFile } from "@/services/agentServices";
import type { AgentQuestion } from "@/types/agent";
import { showToastError } from "@/components/toast";
import { useJobContext } from "@/contexts/JobContext";

// Remove unused fields from Message interface - task status now lives in JobContext

export interface Citation {
  source: string;
  chunk_index: number;
  text: string;
}

export interface ToolStep {
  tool: string;
  status: "running" | "completed";
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  isStream?: boolean;
  citations?: Citation[];
  steps?: ToolStep[];
}

const generateId = () =>
  `msg-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

/** Parse answer - handles JSON wrapper like {"answer": "..."} or {"response": "..."} and removes code block wrappers */
function parseAnswer(answer: string): string {
  if (!answer) return "";

  let content = answer.trim();

  // First, remove markdown code block wrapper if present (e.g., ```json\n...\n```)
  // This must be done BEFORE checking for JSON, because the LLM might wrap the response
  content = content.replace(/^```(?:json|text)?\n?/, "").replace(/```$/, "");

  // Try to parse JSON wrapper if present (after code block removal)
  if (content.startsWith("{") && content.endsWith("}")) {
    try {
      const parsed = JSON.parse(content);
      if (typeof parsed === "object" && parsed !== null) {
        // Common field names that might contain the answer
        const possibleKeys = [
          "answer",
          "response",
          "text",
          "content",
          "message",
        ];
        for (const key of possibleKeys) {
          if (key in parsed && typeof parsed[key] === "string") {
            content = parsed[key];
            break;
          }
        }
        // If single key, use its value
        const keys = Object.keys(parsed);
        if (keys.length === 1 && typeof parsed[keys[0]] === "string") {
          content = parsed[keys[0]];
        }
      }
    } catch {
      // Not valid JSON, continue with original
    }
  }

  return content.trim();
}

interface UseChatStreamParams {
  provider: string;
  model: string;
}

interface UseChatStreamReturn {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isLoading: boolean;
  sessionId: string | null;
  handleQuery: (queryText: string, file?: File | null) => void;
}

export function useChatStream({
  provider,
  model,
}: UseChatStreamParams): UseChatStreamReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { addJob } = useJobContext();

  const handleQuery = useCallback(
    async (query: string, file?: File | null) => {
      if (!query.trim() || isLoading) return;

      // If a file is attached, upload it first to get a UUID
      let fileUuid: string | undefined;
      let fileName: string | undefined;

      if (file) {
        try {
          const result = await uploadAgentFile(file);
          fileUuid = result.file_uuid;
          fileName = result.filename;
        } catch (err) {
          showToastError("Error al subir el archivo");
          setIsLoading(false);
          return;
        }
      }

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: file
          ? `[PDF: ${fileName}]\n${query.trim()}`
          : query.trim(),
      };

      const aiMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, aiMessage]);
      setIsLoading(true);

      const body: AgentQuestion = {
        text: query.trim(),
        session_id: sessionId || undefined,
        file_uuid: fileUuid,
        filename: fileName,
      };

      let accumulatedContent = "";
      const accumulatedSteps: ToolStep[] = [];

      agentAskStream(
        body,
        { provider, model },
        (event, data) => {
          if (event === "tool_start") {
            const toolName: string = data.tool || data.tool_name || "unknown";
            accumulatedSteps.push({ tool: toolName, status: "running" });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, steps: [...accumulatedSteps] }
                  : msg,
              ),
            );
          } else if (event === "tool_done") {
            const toolName: string = data.tool || data.tool_name || "unknown";
            const idx = accumulatedSteps.findLastIndex(
              (s) => s.tool === toolName && s.status === "running",
            );
            if (idx !== -1) {
              accumulatedSteps[idx] = { ...accumulatedSteps[idx], status: "completed" };
            }
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, steps: [...accumulatedSteps] }
                  : msg,
              ),
            );
          } else if (event === "llm_token") {
            accumulatedContent += data.token || "";
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, content: accumulatedContent }
                  : msg,
              ),
            );
          } else if (event === "done") {
            if (data.session_id) {
              setSessionId(data.session_id);
            }
            const finalContent = accumulatedContent || data.answer;
            const currentTaskId = data.task_id || undefined;

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? {
                      ...msg,
                      content: parseAnswer(finalContent),
                      isStreaming: false,
                      citations: data.citations || [],
                      // No more taskId in message - it goes to global context
                    }
                  : msg,
              ),
            );

            // Add task to global context if task_id is present
            // Backend unified: all tasks use same format (status, step, progress)
            if (currentTaskId) {
              addJob({
                id: currentTaskId,
                type: "job",
                source: "agent-chat",
                status: "pending",
                progress: 0,
                message: "Iniciando...",
              });
            }

            setIsLoading(false);
          } else if (event === "error") {
            console.error("Stream error:", data);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? {
                      ...msg,
                      content: "Error: " + (data.error || "Unknown error"),
                      isStreaming: false,
                    }
                  : msg,
              ),
            );
            setIsLoading(false);
          }
        },
        (error) => {
          console.error("Stream error:", error);
          showToastError(error);
          setMessages((prev) => prev.filter((msg) => msg.id !== aiMessage.id));
          setIsLoading(false);
        },
      );
    },
    [isLoading, provider, model, sessionId, addJob],
  );

  return {
    messages,
    setMessages,
    isLoading,
    sessionId,
    handleQuery,
  };
}
