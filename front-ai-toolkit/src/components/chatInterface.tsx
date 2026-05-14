import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { cn } from "@/lib/utils";
import {
  SendHorizontal,
  Loader2,
  Bot,
  Paperclip,
  FileText,
  X,
} from "lucide-react";
import { useLLMConfig, LLMSelector } from "./llmConfigBar";
import { useChatStream } from "@/hooks/useChatStream";
import { MessageBubble } from "./MessageBubble";

export function ChatInterface() {
  const { provider, model, providers, isLoaded, setProvider, setModel } =
    useLLMConfig();

  const { messages, isLoading, handleQuery } = useChatStream({
    provider,
    model,
  });

  const [query, setQuery] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleQueryWrapper = () => {
    if (!query.trim() || isLoading) return;
    handleQuery(query, attachedFile);
    setQuery("");
    setAttachedFile(null);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQueryWrapper();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
        setAttachedFile(file);
      }
    }
    // Reset input so the same file can be re-selected
    e.target.value = "";
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
          {/* File attachment chip */}
          {attachedFile && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/60 border text-sm">
                <FileText className="size-4 text-primary shrink-0" />
                <span className="text-foreground truncate max-w-[200px]">
                  {attachedFile.name}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  ({formatFileSize(attachedFile.size)})
                </span>
                <button
                  type="button"
                  onClick={() => setAttachedFile(null)}
                  className="ml-1 p-0.5 rounded hover:bg-muted-foreground/20 transition-colors"
                >
                  <X className="size-3.5 text-muted-foreground" />
                </button>
              </div>
            </div>
          )}

          <div className="flex items-end gap-3">
            {/* Attach file button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className={cn(
                "shrink-0 p-2 rounded-lg transition-colors",
                attachedFile
                  ? "text-primary bg-primary/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted",
                isLoading && "opacity-50 pointer-events-none",
              )}
              title="Adjuntar PDF"
            >
              <Paperclip className="size-5" />
            </button>

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileSelect}
              className="hidden"
              disabled={isLoading}
            />

            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                className="w-full bg-muted/30 border-0 focus-visible:ring-1 pr-12 text-base"
                placeholder={
                  attachedFile
                    ? "Escribí un mensaje sobre el PDF..."
                    : "Escribí tu pregunta..."
                }
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
