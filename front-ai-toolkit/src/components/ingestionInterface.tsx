import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";
import type { Ingestrequest } from "@/types/rag";
import { ingestURLFetch } from "@/services/ragServices";
import CustomizedToast from "./toast";

function IngestionInterface() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const onURLChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUrl(e.target.value);
  };

  const handleIngest = async () => {
    try {
      setLoading(true);

      new URL(url);

      const body: Ingestrequest = {
        url: url,
      };

      await ingestURLFetch(body);

      CustomizedToast({ type: "info", msg: "Document consumed successfully" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      CustomizedToast({ type: "error", msg: msg });
    } finally {
      setLoading(false);
      setUrl("");
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
            value={url}
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
