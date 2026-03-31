import { useEffect, useState, useCallback } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress.tsx";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { showToast, showToastError, showToastSuccess } from "./toast";

import {
  getJobStatus,
  ingestFileJob,
  ingestURLJob,
} from "@/services/ragServices";
import type { JobStatusResponse } from "@/types/rag";
import { Label } from "./ui/label.tsx";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs.tsx";

export function IngestionInterface() {
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

  const pollJobStatus = useCallback(async (id: string) => {
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const data: JobStatusResponse = await getJobStatus(id);

        let nextMessage = "";

        if (data.status === "completed") nextMessage = "¡Completado!";
        else if (data.status === "running") nextMessage = data.step || "Procesando...";
        else nextMessage = data.status;

        setProgress(data.progress);
        setStatusMessage(nextMessage);

        if (data.status === "completed") {
          setLoading(false);
          setActiveJobId(null);
          setProgress(100);
          showToastSuccess("¡Ingesta completada con éxito!");
        } else if (data.status === "failed") {
          setLoading(false);
          setActiveJobId(null);
          showToastError(`Error: ${data.error || "Desconocido"}`);
        } else {
          timer = setTimeout(poll, 2000);
        }
      } catch (error) {
        setLoading(false);
        setActiveJobId(null);
        console.error("Polling error:", error);
        showToastError("Error al obtener el estado del trabajo");
      }
    };

    poll();

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    let cleanup: (() => void) | undefined;

    if (jobId) {
      pollJobStatus(jobId).then((fn) => {
        cleanup = fn;
      });
    }

    return () => {
      if (cleanup) cleanup();
    };
  }, [jobId, pollJobStatus]);

  const handleIngestJob = async () => {
    if (!url) return;
    setLoading(true);
    setProgress(0);
    setStatusMessage("Iniciando trabajo...");

    try {
      const response = await ingestURLJob({ url, domain, topic });
      if (response.job_id) {
        setActiveJobId(response.job_id);
        showToast({
          type: "info",
          msg: `Trabajo iniciado: ${response.job_id.slice(0, 8)}...`,
        });
      }
    } catch {
      setLoading(false);
      showToastError("No se pudo iniciar la tarea");
    }
  };

  const handleIngestPDFJob = async () => {
    if (!file) {
      showToastError("Por favor selecciona un archivo PDF");
      return;
    }

    setLoading(true);
    setProgress(0);
    setStatusMessage("Subiendo archivo...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", file.name);
    formData.append("domain", domain || "general");
    formData.append("topic", topic || "pdf-upload");

    try {
      const response = await ingestFileJob(formData);

      if (!response.ok) throw new Error("Error en la subida");

      const json = await response.json();
      if (json.job_id) {
        setActiveJobId(json.job_id);
        showToast({
          type: "info",
          msg: `Trabajo iniciado: ${json.job_id.slice(0, 8)}...`,
        });
      }
    } catch (err) {
      setLoading(false);
      showToastError("No se pudo iniciar la tarea");
      console.log(err);
    }
  };

  return (
    <div className="p-4 w-full md:max-w-sm">
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-xl">📥</span>
            Ingesta de Datos
          </CardTitle>
        </CardHeader>

        <Tabs defaultValue="URL" className="w-full">
          <div className="px-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="URL" className="flex items-center gap-2">
                <span>🔗</span> URL
              </TabsTrigger>
              <TabsTrigger value="PDF" className="flex items-center gap-2">
                <span>📄</span> PDF
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="URL" className="animate-slide-up">
            <div className="space-y-4 p-6">
              <Textarea
                placeholder="Pega la URL aquí..."
                value={url}
                onChange={onURLChange}
                className="min-h-[100px] resize-none transition-shadow focus:ring-2 focus:ring-primary/20"
              />
              <Button
                className="w-full"
                onClick={handleIngestJob}
                disabled={loading || !url.startsWith("http")}
                variant={loading ? "secondary" : "gradient"}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span>
                    Procesando...
                  </span>
                ) : (
                  "Ingerir Documento"
                )}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="PDF" className="space-y-4 p-6 animate-slide-up">
            <div className="space-y-2">
              <Label htmlFor="pdf-upload" className="text-sm font-medium">
                Archivo PDF
              </Label>
              <Input
                id="pdf-upload"
                type="file"
                accept=".pdf"
                onChange={onFileChange}
                className="cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
              />
              {file && (
                <p className="text-sm text-muted-foreground truncate">
                  {file.name}
                </p>
              )}
            </div>
            <Button
              className="w-full"
              onClick={handleIngestPDFJob}
              disabled={loading || !file}
              variant={loading ? "secondary" : "gradient"}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Procesando...
                </span>
              ) : (
                "Ingerir Fichero"
              )}
            </Button>
          </TabsContent>
        </Tabs>

        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            <Input
              placeholder="Dominio..."
              value={domain}
              onChange={onChangeDomain}
              className="transition-shadow focus:ring-2 focus:ring-primary/20"
            />

            <Input
              placeholder="Topico..."
              value={topic}
              onChange={onChangeTopic}
              className="transition-shadow focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {loading && (
            <div className="space-y-2 w-full mt-4 border-t pt-4 animate-fade-in">
              <Progress className="h-2 w-full" value={Number(progress)} />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span className="animate-pulse">{statusMessage}</span>
                <span className="font-semibold">{`${Number(progress)}%`}</span>
              </div>
            </div>
          )}

          {!loading && progress === 100 && (
            <div className="mt-4 border-t pt-4 animate-fade-in">
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <span className="text-lg">✅</span>
                <span className="text-sm font-medium">Ingesta completada</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default IngestionInterface;
