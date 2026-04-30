import { Loader2 } from "lucide-react";
import Markdown from "react-markdown";
import { cn } from "@/lib/utils";
import { markdownComponents } from "./markdownComponents";

interface MessageContentProps {
  content: string;
  isStreaming: boolean;
  isUser: boolean;
}

export function MessageContent({
  content,
  isStreaming,
  isUser,
}: MessageContentProps) {
  // Show loading dots only when streaming AND content is empty
  if (isStreaming && !content) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          <span
            className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none text-sm",
        isUser ? "prose-invert" : "prose-neutral",
      )}
    >
      <Markdown components={markdownComponents}>{content}</Markdown>
    </div>
  );
}
