import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { askFetch } from "@/services/ragServices";
import type { Citation, QueryRequest, QueryResponse } from "@/types/rag";
import { toast } from "sonner";
import CustomizedToast from "./toast";

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
              <p className="text-sm">{msg.content}</p>
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
        <Button onClick={handleQuery} disabled={isLoading}>
          Enviar
        </Button>
      </div>
    </div>
  );
}

export default ChatInterface;
