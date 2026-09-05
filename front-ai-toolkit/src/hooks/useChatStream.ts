import { useState, useCallback, useRef } from "react";
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
  agentStatus?:
    | "thinking"
    | "executing_tool"
    | "generating"
    | "waiting_user"
    | "completed";
  currentTool?: string;
  isWaitingForInput?: boolean;
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
  cancelQuery: () => string | null;
}

export function useChatStream({
  provider,
  model,
}: UseChatStreamParams): UseChatStreamReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { addJob } = useJobContext();
  const abortControllerRef = useRef<AbortController | null>(null);
  const pendingQueryRef = useRef<string | null>(null);

  const handleQuery = useCallback(
    async (query: string, file?: File | null) => {
      if (!query.trim() || isLoading) return;

      // Store query so cancelQuery can restore it
      pendingQueryRef.current = query.trim();

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

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
        content: file ? `[PDF: ${fileName}]\n${query.trim()}` : query.trim(),
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
        query: query.trim(),
        sessionId: sessionId || "111",
        file_uuid: fileUuid,
        filename: fileName,
      };

      let accumulatedContent = "";
      const accumulatedSteps: ToolStep[] = [];

      agentAskStream(
        body,
        { provider, model, signal: controller.signal },
        (event, data) => {
          if (event === "state_changed") {
            if (data.state === "executing_tool" && data.tool) {
              accumulatedSteps.push({ tool: data.tool as string, status: "running" });
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id
                    ? {
                        ...msg,
                        steps: [...accumulatedSteps],
                        agentStatus: "executing_tool",
                        currentTool: data.tool as string,
                      }
                    : msg,
                ),
              );
            } else if (data.state === "thinking") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id
                    ? { ...msg, agentStatus: "thinking" }
                    : msg,
                ),
              );
            } else if (data.state === "generating") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id
                    ? { ...msg, agentStatus: "generating" }
                    : msg,
                ),
              );
            } else if (data.state === "waiting_user") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id
                    ? {
                        ...msg,
                        isWaitingForInput: true,
                        agentStatus: "waiting_user",
                      }
                    : msg,
                ),
              );
            } else if (data.state === "completed") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id
                    ? { ...msg, agentStatus: "completed" }
                    : msg,
                ),
              );
            }
          } else if (event === "tool_done") {
            const toolName: string = (data.tool as string) || (data.tool_name as string) || "unknown";
            const idx = accumulatedSteps.findLastIndex(
              (s: ToolStep) => s.tool === toolName && s.status === "running",
            );
            if (idx !== -1) {
              accumulatedSteps[idx] = {
                ...accumulatedSteps[idx],
                status: "completed",
              };
            }
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, steps: [...accumulatedSteps] }
                  : msg,
              ),
            );
          } else if (event === "llm_token") {
            accumulatedContent += (data.token as string) || "";
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, content: accumulatedContent }
                  : msg,
              ),
            );
          } else if (event === "done") {
            if (data.sessionId) {
              setSessionId(data.sessionId as string);
            }
            const finalContent = accumulatedContent || (data.content as string);
            const currentTaskId = data.task_id || undefined;

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? {
                      ...msg,
                      content: parseAnswer(finalContent),
                      isStreaming: false,
                      citations: (data.citations as Citation[]) || [],
                      // No more taskId in message - it goes to global context
                    }
                  : msg,
              ),
            );

            // Add task to global context if task_id is present
            // Backend unified: all tasks use same format (status, step, progress)
            if (currentTaskId) {
              addJob({
                id: currentTaskId as string,
                type: "job",
                source: "agent-chat",
                status: "pending",
                progress: 0,
                message: "Iniciando...",
              });
            }

            setIsLoading(false);
          } else if (event === "state_changed" && data.state === "failed") {
            console.error("Stream error:", data);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? {
                      ...msg,
                      content: "Error: " + ((data.error as string) || "Unknown error"),
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

  const cancelQuery = useCallback((): string | null => {
    // Abort the in-flight fetch
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    // Remove the last user message AND the streaming assistant placeholder
    setMessages((prev) => {
      const lastUserIdx = prev.findLastIndex((msg: Message) => msg.role === "user");
      if (lastUserIdx === -1)
        return prev.filter((msg) => msg.isStreaming !== true);
      // Remove user message at lastUserIdx and everything after (the AI placeholder)
      return prev.slice(0, lastUserIdx);
    });
    setIsLoading(false);

    // Return the pending query text so the caller can restore it to the input
    const queryText = pendingQueryRef.current;
    pendingQueryRef.current = null;
    return queryText;
  }, []);

  return {
    messages,
    setMessages,
    isLoading,
    sessionId,
    handleQuery,
    cancelQuery,
  };
}
