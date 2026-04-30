import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import Markdown from "react-markdown";
import { cn } from "@/lib/utils";
import { SendHorizontal, Loader2, Bot, User } from "lucide-react";
import { useLLMConfig, LLMSelector } from "./llmConfigBar";
import { useChatStream, type Message } from "@/hooks/useChatStream";
import { markdownComponents } from "./markdownComponents";

export function ChatInterface() {
  const { provider, model, providers, isLoaded, setProvider, setModel } =
    useLLMConfig();

  const { messages, isLoading, handleQuery } = useChatStream({
    provider,
    model,
  });

  const [query, setQuery] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleQueryWrapper = () => {
    handleQuery(query);
    setQuery("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQueryWrapper();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header con selector de LLM */}
      <div className="shrink-0 px-4 py-2 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">LLM:</span>
        </div>
        <LLMSelector
          provider={provider}
          model={model}
          providers={providers}
          onProviderChange={setProvider}
          onModelChange={setModel}
          isLoading={!isLoaded}
        />
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="shrink-0 border-t bg-background/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                className="w-full bg-muted/30 border-0 focus-visible:ring-1 pr-12 text-base"
                placeholder="Escribí tu pregunta..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
              />
            </div>
            <Button
              onClick={handleQueryWrapper}
              disabled={isLoading || !query.trim()}
              size="icon-lg"
              className={cn(
                "shrink-0 transition-all",
                query.trim() && "bg-primary hover:bg-primary/90",
              )}
            >
              {isLoading ? (
                <Loader2 className="size-5 animate-spin" />
              ) : (
                <SendHorizontal className="size-5" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Presioná Enter para enviar · Shift + Enter para nueva línea
          </p>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-6 animate-in fade-in duration-500">
      <div className="p-5 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5">
        <Bot className="size-14 text-primary" />
      </div>
      <div className="space-y-2 max-w-md">
        <h3 className="text-xl font-semibold">¿En qué puedo ayudarte?</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Hacé preguntas sobre tus documentos ingestados. El agente usará el
          contexto disponible para darte respuestas precisas y detalladas.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {[
          "¿Qué contiene este documento?",
          "Resume lo más importante",
          "Explica el concepto principal",
        ].map((suggestion) => (
          <button
            key={suggestion}
            className="text-xs px-3 py-1.5 rounded-full bg-muted/50 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground border border-transparent hover:border-border"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
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
      {/* Avatar */}
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

      {/* Message */}
      <div
        className={cn(
          "flex-1 max-w-[85%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        {/* Tool Status (e.g., "Searching documents...") */}
        {message.toolStatus && (
          <div className="text-xs text-muted-foreground mb-1 italic">
            {message.toolStatus}
          </div>
        )}

        <div
          className={cn(
            "px-4 py-3 rounded-2xl",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted/50 border-0",
          )}
        >
          {message.isStreaming && !message.content ? (
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
          ) : (
            <div
              className={cn(
                "prose prose-sm max-w-none text-sm",
                isUser ? "prose-invert" : "prose-neutral",
              )}
            >
              <Markdown components={markdownComponents}>
                {message.content}
              </Markdown>
            </div>
          )}
        </div>

        {/* Citations - Unique Sources Only */}
        {uniqueSources.length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground">
            <p className="font-semibold mb-1">Sources:</p>
            <ul className="list-disc list-outside pl-4 space-y-0.5">
              {uniqueSources.map((source, idx) => (
                <li key={idx} className="italic">
                  {source}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
