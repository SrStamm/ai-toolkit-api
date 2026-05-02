import { useState, useCallback } from "react";
import { agentAskStream } from "@/services/agentServices";
import type { AgentQuestion } from "@/types/agent";
import { showToastError } from "@/components/toast";

export interface Citation {
  source: string;
  chunk_index: number;
  text: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  isStream?: boolean;
  citations?: Citation[];
  toolStatus?: string;
  taskId?: string; // Celery task ID for background jobs (e.g., reindex)
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
  handleQuery: (queryText: string) => void;
}

export function useChatStream({
  provider,
  model,
}: UseChatStreamParams): UseChatStreamReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleQuery = useCallback(
    (query: string) => {
      if (!query.trim() || isLoading) return;

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: query.trim(),
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
      };

      let accumulatedContent = "";
      let currentTool = "";

      agentAskStream(
        body,
        { provider, model },
        (event, data) => {
          if (event === "agent_decision") {
            // Router decision - optional UI update
          } else if (event === "tool_start") {
            currentTool = data.tool || "unknown";
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, toolStatus: `Using ${currentTool}...` }
                  : msg,
              ),
            );
          } else if (event === "tool_done") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? { ...msg, toolStatus: `Completed ${currentTool}` }
                  : msg,
              ),
            );
            setTimeout(() => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessage.id &&
                  msg.toolStatus?.includes("Completed")
                    ? { ...msg, toolStatus: undefined }
                    : msg,
                ),
              );
            }, 1500);
            currentTool = "";
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
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessage.id
                  ? {
                      ...msg,
                      content: parseAnswer(finalContent),
                      isStreaming: false,
                      citations: data.citations || [],
                      toolStatus: undefined,
                      // Capture Celery task_id if present in metadata
                      taskId: data.task_id || undefined, 
                    }
                  : msg,
              ),
            );
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
                      toolStatus: undefined,
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
    [isLoading, provider, model, sessionId],
  );

  return {
    messages,
    setMessages,
    isLoading,
    sessionId,
    handleQuery,
  };
}
