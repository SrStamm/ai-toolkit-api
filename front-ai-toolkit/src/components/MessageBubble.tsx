import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { Message } from "@/hooks/useChatStream";
import { MessageAvatar } from "./MessageAvatar";
import { ToolStatus } from "./ToolStatus";
import { MessageContent } from "./MessageContent";
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
        {/* Tool Status (e.g., "Searching documents...") */}
        {message.toolStatus && <ToolStatus status={message.toolStatus} />}

        <div
          className={cn(
            "px-4 py-3 rounded-2xl",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted/50 border-0",
          )}
        >
          <MessageContent
            content={message.content}
            isStreaming={!!message.isStreaming}
            isUser={isUser}
          />
        </div>

        {/* Citations - Unique Sources Only */}
        <CitationsList sources={uniqueSources} />
      </div>
    </div>
  );
}
