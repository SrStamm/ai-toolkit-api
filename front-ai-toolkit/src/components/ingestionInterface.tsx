import React, { useEffect, useState } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress.tsx";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import CustomizedToast from "./toast";

import {
  getJobStatus,
  ingestFileJob,
  ingestURLJob,
} from "@/services/ragServices";
import { Label } from "./ui/label.tsx";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs.tsx";

function IngestionInterface() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setActiveJobId] = useState<string | null>(null);

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

  useEffect(() => {
    let timer: number;

    const poll = async () => {
      if (!jobId) return;

      try {
        const data = await getJobStatus(jobId);

        let nextMessage = "";

        if (data.status === "completed") nextMessage = "¡Completado!";
        else if (data.status === "running")
          nextMessage = data.step || "Procesando...";
        else nextMessage = data.status;

        setProgress(data.progress);
        setStatusMessage(nextMessage);

        console.log(
          "Estado actual del Job:",
          data.progress,
          "% -",
          nextMessage,
        );
        console.log("data", data);

        if (data.status === "running") setStatusMessage("Procesando...");

        if (data.status === "completed") {
          setLoading(false);
          setActiveJobId(null);
          setProgress(100);
          CustomizedToast({
            type: "success",
            msg: "¡Ingesta completada con éxito!",
          });
        } else if (data.status === "failed") {
          setLoading(false);
          setActiveJobId(null);
          CustomizedToast({
            type: "error",
            msg: `Error: ${data.error || "Desconocido"}`,
          });
        } else {
          // Sigue preguntando cada 2 segundos
          timer = setTimeout(poll, 500);
        }
      } catch (error) {
        setLoading(false);
        console.error("Polling error:", error);
      }
    };

    if (jobId) {
      poll();
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  const handleIngestJob = async () => {
    if (!url) return;
    setLoading(true);
    setProgress(0);

    try {
      const response = await ingestURLJob({ url, domain, topic });
      if (response.job_id) {
        setActiveJobId(response.job_id);
      }
    } catch {
      setLoading(false);
      CustomizedToast({ type: "error", msg: "No se pudo iniciar la tarea" });
    }
  };

  const handleIngestPDFJob = async () => {
    if (!file) {
      CustomizedToast({
        type: "error",
        msg: "Por favor selecciona un archivo PDF",
      });
      return;
    }

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
      const response = await ingestFileJob(formData);

      if (!response.ok) throw new Error("Error en la subida");

      const json = await response.json();
      if (json.job_id) {
        setActiveJobId(json.job_id);
      }
    } catch (err) {
      setLoading(false);
      CustomizedToast({ type: "error", msg: "No se pudo iniciar la tarea" });
      console.log(err);
    }
  };

  return (
    <div className="p-4 w-full md:max-w-sm">
      <Card>
        <CardHeader>
          <CardTitle>Ingesta de Datos</CardTitle>
        </CardHeader>

        <Tabs defaultValue="URL" className="w-full">
          <div className="px-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="URL">URL</TabsTrigger>
              <TabsTrigger value="PDF">PDF</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="URL">
            <div className="space-y-4 p-6">
              <Textarea
                placeholder="Pega la URL aquí..."
                value={url}
                onChange={onURLChange}
              />
              <Button
                className="w-full"
                onClick={handleIngestJob}
                disabled={loading || !url.startsWith("http")}
              >
                Ingerir Documento
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="PDF" className="space-y-4 p-6">
            <div className="space-y-2">
              <Label htmlFor="pdf-upload">Archivo PDF</Label>
              <Input
                id="pdf-upload"
                type="file"
                accept=".pdf"
                onChange={onFileChange}
                className="cursor-pointer"
              />
            </div>
            <Button
              className="w-full"
              onClick={handleIngestPDFJob}
              disabled={loading || !file}
            >
              {loading ? "Procesando..." : "Ingerir Fichero"}
            </Button>
          </TabsContent>
        </Tabs>

        <CardContent>
          <div className="grid grid-cols-2 gap-2">
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

          {loading && (
            <div className="space-y-2 w-full mt-4 border-t pt-4">
              <Progress className="h-2 w-full" value={Number(progress)} />
              <div className="flex justify-between text-xs text-muted-foreground animate-pulse">
                <span>{statusMessage || "Procesando..."}</span>
                <span>{`${Number(progress)}%`}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default IngestionInterface;
