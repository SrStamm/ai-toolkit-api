import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageAvatarProps {
  role: "user" | "assistant";
}

export function MessageAvatar({ role }: MessageAvatarProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
        isUser ? "bg-primary/10" : "bg-muted",
      )}
    >
      {isUser ? (
        <User className="size-4 text-primary" />
      ) : (
        <Bot className="size-4 text-muted-foreground" />
      )}
    </div>
  );
}
