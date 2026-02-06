import React, { useId, useState } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress.tsx";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import CustomizedToast from "./toast";

import type { Ingestrequest } from "@/types/rag";
import { ingestFile, ingestURLStream } from "@/services/ragServices";
import { Label } from "./ui/label.tsx";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs.tsx";

function IngestionInterface() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [fileId, setFileId] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const InputFileDemo = () => {
    const id = useId();
    setFileId(id);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const onChangeDomain = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDomain(e.target.value);
  };

  const onChangeTopic = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTopic(e.target.value);
  };

  const onURLChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUrl(e.target.value);
  };

  // --- Function to ingest without stream ---

  // const handleIngest = async () => {
  //   try {
  //     setLoading(true);

  //     new URL(url);

  //     const body: Ingestrequest = {
  //       url: url,
  //       domain: typeof domain === "string" ? domain : undefined,
  //       topic: typeof topic === "string" ? topic : undefined,
  //     };

  //     await ingestURLFetch(body);

  //     CustomizedToast({ type: "info", msg: "Document consumed successfully" });
  //   } catch (err) {
  //     const msg = err instanceof Error ? err.message : "Unknown error";
  //     CustomizedToast({ type: "error", msg: msg });
  //   } finally {
  //     setLoading(false);
  //     setUrl("");
  //   }
  // };

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
      }
    } finally {
      setLoading(false);
      setUrl("");
    }
  };

  const handleIngestPDFStream = async () => {
    if (!file) {
      CustomizedToast({
        type: "error",
        msg: "Por favor selecciona un archivo PDF",
      });
      return;
    }

    try {
      setLoading(true);
      setProgress(0);

      // Create FormData container
      const formData = new FormData();

      // Add the fields
      formData.append("file", file);
      formData.append("source", file.name);
      formData.append("domain", domain || "general");
      formData.append("topic", topic || "pdf-upload");

      try {
        // Fetch
        const response = await ingestFile(formData);

        if (!response.ok) throw new Error("Error en la subida");

        // Stream logic
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
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 w-full max-w-sm">
      <Card>
        <Tabs defaultValue="URL">
          <CardHeader>
            <CardTitle>Ingesta de Datos</CardTitle>
          </CardHeader>

          <TabsList>
            <TabsTrigger value="URL">URL</TabsTrigger>
            <TabsTrigger value="PDF">PDF</TabsTrigger>
          </TabsList>
        </Tabs>

        <TabsContent value="URL">
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
          </CardContent>
        </TabsContent>

        <TabsContent value="PDF">
          <CardContent className="w-full max-w-xs space-y-2">
            <Label htmlFor={fileId}>File input</Label>
            <Input
              id="pdf-upload"
              type="file"
              className="text-muted-foreground file:border-input file:text-foreground p-0 pr-3 italic file:mr-3 file:h-full file:border-0 file:border-r file:border-solid file:bg-transparent file:px-3 file:text-sm file:font-medium file:not-italic"
              accept=".pdf"
              onClick={InputFileDemo}
              onChange={onFileChange}
            />
            <Button
              className="w-full"
              onClick={handleIngestPDFStream}
              disabled={loading || !file}
            >
              {loading ? "Procesando..." : "Ingerir Fichero"}
            </Button>
          </CardContent>
        </TabsContent>

        <Input
          placeholder="Dominio..."
          value={domain}
          onChange={onChangeDomain}
        />

        <Input placeholder="Topico..." value={topic} onChange={onChangeTopic} />

        {loading ? (
          <div className="space-y-2 w-full mt-4">
            <Progress className="h-2 w-full" value={Number(progress)} />
            <p className="text-sm text-muted-foreground animate-pulse">
              {`${Number(progress)}%`}
            </p>
            <p className="text-sm text-muted-foreground animate-pulse">
              {statusMessage || "Iniciando ingesta"}
            </p>
          </div>
        ) : (
          ""
        )}
      </Card>
    </div>
  );
}

export default IngestionInterface;
