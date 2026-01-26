import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";
import type { Ingestrequest } from "@/types/rag";
import { ingestURLFetch } from "@/services/ragServices";

function IngestionInterface() {
  const [URL, setURL] = useState("");
  const [loading, setLoading] = useState(false);

  const onURLChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setURL(e.target.value);
  };

  const handleIngest = async () => {
    try {
      setLoading(true);

      const body: Ingestrequest = {
        url: URL,
      };

      await ingestURLFetch(body);
    } finally {
      setLoading(false);
      setURL("");
    }
  };

  return (
    <div className="p-4 w-full max-w-sm">
      <Card>
        <CardHeader>
          <CardTitle>Ingesta de Datos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Pega la URL aquí..."
            value={URL}
            onChange={onURLChange}
          />
          <Button className="w-full" onClick={handleIngest} disabled={loading}>
            Ingerir Documento
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default IngestionInterface;
