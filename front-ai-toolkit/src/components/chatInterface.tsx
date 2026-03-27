import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { agentAsk } from "@/services/agentServices";
import type { AgentQuestion } from "@/types/agent";
import CustomizedToast from "./toast";
import Markdown from "react-markdown";

interface Message {
  role: "user" | "ai";
  content: string;
}

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const onChangeQuery = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleQuery = async () => {
    setIsLoading(true);

    const userMessage: Message = {
      role: "user",
      content: query,
    };

    setMessages((prev) => [...prev, userMessage]);

    const aiMessage: Message = {
      role: "ai",
      content: "",
    };

    setMessages((prev) => [...prev, aiMessage]);

    const body: AgentQuestion = {
      text: query,
      session_id: sessionId || undefined,
    };

    setQuery("");

    try {
      const response = await agentAsk(body);

      // Update session ID for future requests
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      // Add the response content
      aiMessage.content = response.output;
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = { ...aiMessage };
        return newMessages;
      });

      // Show metadata if available
      if (response.metadata && Object.keys(response.metadata).length > 0) {
        console.log("Agent metadata:", response.metadata);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      CustomizedToast({ type: "error", msg: msg });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-2 md:p-4 w-full overflow-hidden">
      {/* Area de mensajes */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 border rounded-lg min-h-0">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <Card
              className={`p-3 max-w-[80%] ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}
            >
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
                  code: ({ children, className, ...props }) => {
                    const isBlock = className?.includes("language");
                    const textColor = isBlock
                      ? "text-slate-300"
                      : msg.role === "user"
                        ? "text-white"
                        : "text-black font-bold";
                    return (
                      <code
                        className={`${textColor} px-1.5 py-0.5 rounded-sm text-sm`}
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                  pre: ({ children }) => (
                    <pre className="bg-slate-900 p-4 rounded-md overflow-x-auto text-left my-2">
                      {children}
                    </pre>
                  ),
                }}
              >
                {msg.content}
              </Markdown>
            </Card>
          </div>
        ))}
      </div>

      {/* Input de Pregunta */}
      <div className="flex gap-2 shrink-0 bg-background pt-2">
        <Input
          className="flex-1"
          placeholder="Haz una pregunta al agente..."
          value={query}
          onChange={onChangeQuery}
          disabled={isLoading}
        />

        <Button onClick={handleQuery} disabled={isLoading || !query.trim()}>
          Enviar
        </Button>
      </div>
    </div>
  );
}

export default ChatInterface;
