import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { askStreamFetch } from "@/services/ragServices";
import type { Citation, QueryRequest } from "@/types/rag";
import CustomizedToast from "./toast";
import Markdown from "react-markdown";

interface Message {
  role: "user" | "ai";
  content: string;
  citations?: Citation[];
}

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const onChangeQuery = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const onChangeDomain = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDomain(e.target.value);
  };

  const onChangeTopic = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTopic(e.target.value);
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

    const body: QueryRequest = {
      text: query,
      domain: typeof domain === "string" ? domain : undefined,
      topic: typeof topic === "string" ? topic : undefined,
    };

    setQuery("");

    try {
      const response = await askStreamFetch(body);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");

        buffer = parts.pop() || "";

        for (const line of parts) {
          const trimmedLine = line.trim();
          if (!trimmedLine || !trimmedLine.startsWith("data: ")) continue;

          try {
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
                <span className="text-xs text-gray-500">
                  {data.tokens} tokens · ${data.cost.toFixed(4)}
                </span>;
                break;

              case "error":
                CustomizedToast({ type: "error", msg: data.content });
                break;

              case "done":
                break;
            }
          } catch {
            console.error("Error parseando JSON incompleto:", trimmedLine);
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
              {msg.citations &&
                msg.citations.length > 0 &&
                msg.citations.map((c) => (
                  <div
                    key={c.chunk_index}
                    className="mt-2 pt-2 border-t text-xs text-blue-500"
                  >
                    {c.source}
                  </div>
                ))}
            </Card>
          </div>
        ))}
      </div>

      {/* Input de Pregunta */}
      <div className="flex gap-2 shrink-0 bg-background pt-2">
        <div className="flex-col flex-1 space-y-2">
          <Input
            placeholder="Haz una pregunta sobre los documentos..."
            value={query}
            onChange={onChangeQuery}
          />

          <div className="flex gap-2 ">
            <Input
              placeholder="Dominio..."
              value={domain}
              onChange={onChangeDomain}
            />

            <Input
              placeholder="Topico..."
              value={topic}
              onChange={onChangeTopic}
            />
          </div>
        </div>

        <Button onClick={handleQueryStream} disabled={isLoading}>
          Enviar
        </Button>
      </div>
    </div>
  );
}

export default ChatInterface;
