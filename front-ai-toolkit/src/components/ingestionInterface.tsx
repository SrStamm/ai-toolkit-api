import React, { useState } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";
import type { Ingestrequest } from "@/types/rag";
import { ingestURLFetch, ingestURLStream } from "@/services/ragServices";
import CustomizedToast from "./toast";
import { Input } from "./ui/input";

function IngestionInterface() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");

  const onChangeDomain = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDomain(e.target.value);
  };

  const onChangeTopic = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTopic(e.target.value);
  };

  const onURLChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUrl(e.target.value);
  };

  const handleIngest = async () => {
    try {
      setLoading(true);

      new URL(url);

      const body: Ingestrequest = {
        url: url,
        domain: typeof domain === "string" ? domain : undefined,
        topic: typeof topic === "string" ? topic : undefined,
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

  const handleIngestStream = async () => {
    try {
      setLoading(true);

      new URL(url);

      const body: Ingestrequest = {
        url: url,
        domain: typeof domain === "string" ? domain : undefined,
        topic: typeof topic === "string" ? topic : undefined,
      };

      try {
        const response = await ingestURLStream(body);

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n\n").filter((line) => line.trim());

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = JSON.parse(line.slice(6));

              if (data.error) {
                CustomizedToast({ type: "error", msg: data.error });
                break;
              }

              setProgress(data.progress);
              setStatusMessage(data.step);

              console.log(data.progress);
              console.log(data.step);

              if (data.progress === 100) {
                CustomizedToast({
                  type: "success",
                  msg: `Processed ${data.chunks_processed} chunks`,
                });
                break;
              }
            }
          }
        }
      } catch (error) {
        CustomizedToast({ type: "error", msg: String(error) });
        return;
      }
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
          <Button
            className="w-full"
            onClick={handleIngestStream}
            disabled={loading}
          >
            Ingerir Documento
          </Button>

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
        </CardContent>
      </Card>
    </div>
  );
}

export default IngestionInterface;
