import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { askFetch } from "@/services/ragServices";
import type { QueryRequest, QueryResponse } from "@/types/rag";

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [answer, setAnswer] = useState("");

  const onChangeQuery = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleQuery = async () => {
    setIsLoading(true);
    try {
      const body: QueryRequest = {
        text: query,
      };
      const response: QueryResponse = await askFetch(body);

      setAnswer(response.answer);
      console.log(response);
    } finally {
      setIsLoading(false);
      setQuery("");
    }
  };

  return (
    <div className="flex flex-col h-[90vh] p-4 w-full">
      {/* Area de mensajes */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 border rounded-lg">
        <Card className="p-3 bg-muted">
          <p className="text-sm">Aquí aparecerá la respuesta de la IA...</p>
          <p>{answer}</p>
          <div className="mt-2 pt-2 border-t text-xs text-blue-500">
            Citations: source-url.com
          </div>
        </Card>
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
