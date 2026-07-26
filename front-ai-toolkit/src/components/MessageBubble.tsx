import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import type { Message } from "@/hooks/useChatStream";
import { MessageAvatar } from "./MessageAvatar";
import { MessageContent } from "./MessageContent";
import { ToolSteps } from "./ToolSteps";
import { CitationsList } from "./CitationsList";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Get unique sources from citations
  const uniqueSources = useMemo(() => {
    if (!message.citations || message.citations.length === 0) return [];
    return [...new Set(message.citations.map((c) => c.source))];
  }, [message.citations]);

  return (
    <div
      className={cn(
        "flex gap-3 animate-in slide-in-from-bottom-4 fade-in duration-300",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <MessageAvatar role={message.role} />

      <div
        className={cn(
          "flex-1 max-w-[85%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "px-4 py-3 rounded-2xl",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted/50 border-0",
          )}
        >
          {!isUser && message.steps && message.steps.length > 0 && (
            <ToolSteps steps={message.steps} />
          )}

          {!isUser && message.agentStatus && message.agentStatus !== "completed" && (
            <div className="flex items-center gap-1.5 mb-2 text-xs text-muted-foreground">
              {message.agentStatus === "thinking" && (
                <>
                  <Loader2 className="size-3 animate-spin" />
                  <span>Analizando...</span>
                </>
              )}
              {message.agentStatus === "generating" && (
                <>
                  <span className="inline-block size-1.5 rounded-full bg-primary animate-pulse" />
                  <span>Generando respuesta...</span>
                </>
              )}
            </div>
          )}

          <MessageContent
            content={message.content}
            isStreaming={!!message.isStreaming}
            isUser={isUser}
          />

          {!isUser && message.isWaitingForInput && (
            <div className="flex items-center gap-1.5 mt-2 text-xs text-amber-600 dark:text-amber-400">
              <span className="inline-block size-1.5 rounded-full bg-amber-500 animate-pulse" />
              <span className="font-medium">Esperando tu respuesta...</span>
            </div>
          )}
        </div>

        {/* Citations - Unique Sources Only */}
        <CitationsList sources={uniqueSources} />
      </div>
    </div>
  );
}
