import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { agentAsk } from "@/services/agentServices";
import type { AgentQuestion } from "@/types/agent";
import { showToastError } from "./toast";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  isStreaming?: boolean;
}

const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export function ChatInterface() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleQuery = async () => {
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: query.trim(),
    };

    const aiMessage: Message = {
      id: generateId(),
      role: "ai",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);
    setIsLoading(true);
    setQuery("");

    const body: AgentQuestion = {
      text: query.trim(),
      session_id: sessionId || undefined,
    };

    try {
      const response = await agentAsk(body);

      if (response.session_id) {
        setSessionId(response.session_id);
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessage.id
            ? { ...msg, content: response.output, isStreaming: false }
            : msg
        )
      );

      if (response.metadata && Object.keys(response.metadata).length > 0) {
        console.log("Agent metadata:", response.metadata);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      showToastError(errorMessage);
      setMessages((prev) => prev.filter((msg) => msg.id !== aiMessage.id));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  return (
    <div className="flex flex-col h-full p-2 md:p-4 w-full overflow-hidden">
      {/* Area de mensajes */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 border rounded-lg min-h-0 bg-muted/20">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground animate-fade-in">
            <div className="text-4xl mb-4">💬</div>
            <p className="text-lg font-medium">Comienza una conversación</p>
            <p className="text-sm">Escribe una pregunta abajo para empezar</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-up`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <Card
              className={`p-3 max-w-[80%] transition-all duration-200 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground shadow-md"
                  : "bg-card"
              } ${msg.isStreaming ? "animate-pulse" : ""}`}
            >
              {msg.isStreaming ? (
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-current rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span className="text-sm text-muted-foreground">Pensando...</span>
                </div>
              ) : (
                <Markdown
                  components={{
                    p: ({ children }) => (
                      <p className="mb-2 last:mb-0 text-left">{children}</p>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-disc list-outside pl-5 mb-2 space-y-1 text-left">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="list-decimal list-outside pl-5 mb-2 space-y-1 text-left">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => (
                      <li className="text-left leading-relaxed">{children}</li>
                    ),
                    strong: ({ children }) => (
                      <strong className="font-semibold">{children}</strong>
                    ),
                    code: ({ className, children }) => {
                      const match = /language-(\w+)/.exec(className || "");
                      const isInline = !match && !className?.includes("language");

                      if (isInline) {
                        return (
                          <code className="bg-slate-200 dark:bg-slate-700 px-1.5 py-0.5 rounded text-sm font-mono">
                            {children}
                          </code>
                        );
                      }

                      return (
                        <SyntaxHighlighter
                          // eslint-disable-next-line @typescript-eslint/no-explicit-any
                          style={vscDarkPlus as any}
                          language={match ? match[1] : "text"}
                          PreTag="div"
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      );
                    },
                    pre: ({ children }) => <>{children}</>,
                  }}
                >
                  {msg.content}
                </Markdown>
              )}
            </Card>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input de Pregunta */}
      <div className="flex gap-2 shrink-0 bg-background pt-2">
        <Input
          ref={inputRef}
          className="flex-1 transition-shadow focus:ring-2 focus:ring-primary/20"
          placeholder="Haz una pregunta al agente..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />

        <Button
          onClick={handleQuery}
          disabled={isLoading || !query.trim()}
          variant="gradient"
          className="min-w-[100px]"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="animate-spin">⏳</span>
              Enviando...
            </span>
          ) : (
            "Enviar"
          )}
        </Button>
      </div>
    </div>
  );
}

export default ChatInterface;
