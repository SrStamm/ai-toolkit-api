import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { askFetch } from "@/services/ragServices";
import type { Citation, QueryRequest, QueryResponse } from "@/types/rag";
import CustomizedToast from "./toast";
import Markdown from "react-markdown";

interface Message {
  role: "user" | "ai";
  content: string;
  citations?: Citation[];
}

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const onChangeQuery = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleQuery = async () => {
    setIsLoading(true);

    try {
      const body: QueryRequest = {
        text: query,
      };

      const user_message: Message = {
        role: "user",
        content: query,
      };

      setMessages((prev) => [...prev, user_message]);

      setQuery("");

      const response: QueryResponse = await askFetch(body);

      const ai_message: Message = {
        role: "ai",
        content: response.answer,
        citations: response.citations,
      };

      setMessages((prev) => [...prev, ai_message]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      CustomizedToast({ type: "error", msg: msg });
    } finally {
      setIsLoading(false);
      setQuery("");
    }
  };

  const handleQueryStream = async () => {
    setIsLoading(true);

    const userMessage: Message = {
      role: "user",
      content: query,
    };

    setMessages((prev) => [...prev, userMessage]);

    const aiMessage: Message = {
      role: "ai",
      content: "",
      citations: [],
    };

    setMessages((prev) => [...prev, aiMessage]);
    setQuery("");

    try {
      const response = await fetch("http://localhost:8000/rag/ask-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: query,
          domain: null,
          topic: null,
        }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n").filter((line) => line.trim());

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));

            switch (data.type) {
              case "content":
                aiMessage.content += data.content;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...aiMessage };
                  return newMessages;
                });
                break;

              case "citations":
                aiMessage.citations = data.citations;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...aiMessage };
                  return newMessages;
                });
                break;

              case "metadata":
                // Mostrar tokens/costo al usuario (opcional)
                console.log(
                  `Tokens: ${data.tokens}, Cost: $${data.cost.toFixed(6)}`,
                );
                // O agregar un badge en la UI:
                // <span className="text-xs text-gray-500">
                //   {data.tokens} tokens · ${data.cost.toFixed(4)}
                // </span>
                break;

              case "error":
                CustomizedToast({ type: "error", msg: data.content });
                break;

              case "done":
                console.log("Stream completed");
                break;
            }
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      CustomizedToast({ type: "error", msg: msg });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[90vh] p-4 w-full">
      {/* Area de mensajes */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 border rounded-lg">
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
                    <p className="mb-2 last:mb-0 text-left ">{children}</p>
                  ),
                  code: ({ children, className, ...props }) => {
                    const isBlock = className?.includes("language");

                    let textColor = "";

                    if (isBlock) {
                      textColor = "text-slate-300";
                    } else {
                      textColor =
                        msg.role === "user"
                          ? "text-white"
                          : "text-black font-bold";
                    }

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
                    <pre className="bg-slate-900 p-4 rounded-md overflow-x-auto text-left">
                      {children}
                    </pre>
                  ),
                }}
              >
                {msg.content}
              </Markdown>
              {msg.citations &&
                msg.citations.length > 0 &&
                msg.citations.map((c) => (
                  <div className="mt-2 pt-2 border-t text-xs text-blue-500">
                    {c.source}
                  </div>
                ))}
            </Card>
          </div>
        ))}
      </div>

      {/* Input de Pregunta */}
      <div className="flex gap-2">
        <Input
          placeholder="Haz una pregunta sobre los documentos..."
          value={query}
          onChange={onChangeQuery}
        />
        <Button onClick={handleQueryStream} disabled={isLoading}>
          Enviar
        </Button>
      </div>
    </div>
  );
}

export default ChatInterface;
