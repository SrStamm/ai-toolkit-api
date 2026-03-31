import { useEffect, useState, useCallback, useRef } from "react";
import { Button } from "./ui/button";
import { CardContent } from "./ui/card";
import { Progress } from "./ui/progress";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { showToast, showToastError, showToastSuccess } from "./toast";
import { getJobStatus, ingestFileJob, ingestURLJob } from "@/services/ragServices";
import type { JobStatusResponse } from "@/types/rag";
import { Label } from "./ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { cn } from "@/lib/utils";
import { 
  Globe, 
  FileText, 
  Upload, 
  Link2, 
  CheckCircle2, 
  Loader2,
  XCircle,
  FileUp,
  Sparkles,
  ChevronRight
} from "lucide-react";

export function IngestionInterface() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setActiveJobId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingTimerRef = useRef<number | null>(null);

  const isValidUrl = url.startsWith("http://") || url.startsWith("https://");

  const pollJobStatus = useCallback(async (id: string) => {
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
        
        setTimeout(() => {
          setProgress(0);
          setStatusMessage("");
        }, 3000);
      } else if (data.status === "failed") {
        setLoading(false);
        setActiveJobId(null);
        showToastError(`Error: ${data.error || "Desconocido"}`);
      } else {
        pollingTimerRef.current = window.setTimeout(() => pollJobStatus(id), 2000);
      }
    } catch (error) {
      setLoading(false);
      setActiveJobId(null);
      console.error("Polling error:", error);
      showToastError("Error al obtener el estado del trabajo");
    }
  }, []);

  useEffect(() => {
    if (jobId) {
      pollJobStatus(jobId);
    }

    return () => {
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
      }
    };
  }, [jobId, pollJobStatus]);

  const handleIngestJob = async () => {
    if (!isValidUrl) return;
    setLoading(true);
    setProgress(0);
    setStatusMessage("Iniciando...");

    try {
      const response = await ingestURLJob({ url, domain, topic });
      if (response.job_id) {
        setActiveJobId(response.job_id);
        showToast({ msg: "Trabajo iniciado", type: "info" });
      }
    } catch {
      setLoading(false);
      showToastError("No se pudo iniciar la tarea");
    }
  };

  const handleIngestPDFJob = async () => {
    if (!file) {
      showToastError("Selecciona un archivo PDF primero");
      return;
    }

    setLoading(true);
    setProgress(0);
    setStatusMessage("Subiendo...");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", file.name);
    formData.append("domain", domain || "general");
    formData.append("topic", topic || "pdf-upload");

    try {
      const response = await ingestFileJob(formData);

      if (!response.ok) throw new Error("Error en la subida");

      const json = await response.json() as { job_id: string };
      if (json.job_id) {
        setActiveJobId(json.job_id);
        showToast({ msg: "Archivo subido", type: "info" });
      }
    } catch {
      setLoading(false);
      showToastError("No se pudo iniciar la tarea");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile);
    } else {
      showToastError("Solo se permiten archivos PDF");
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-primary/10">
            <Sparkles className="size-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Ingesta de Datos</h2>
            <p className="text-xs text-muted-foreground">
              Cargá documentos para que el agente pueda responder
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 pt-4">
        <Tabs defaultValue="url" className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-muted/50">
            <TabsTrigger value="url" className="gap-2 data-[state=active]:bg-background">
              <Link2 className="size-4" />
              URL
            </TabsTrigger>
            <TabsTrigger value="pdf" className="gap-2 data-[state=active]:bg-background">
              <FileText className="size-4" />
              PDF
            </TabsTrigger>
          </TabsList>

          {/* URL Tab */}
          <TabsContent value="url" className="space-y-4 mt-4">
            <div className="space-y-3">
              <Label className="text-sm font-medium">URL del documento</Label>
              <div className="relative">
                <Textarea
                  placeholder="https://ejemplo.com/documento"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className={cn(
                    "min-h-[100px] resize-none transition-all",
                    url && !isValidUrl && "border-destructive focus:border-destructive"
                  )}
                />
                {url && (
                  <div className="absolute right-3 top-3">
                    {isValidUrl ? (
                      <CheckCircle2 className="size-5 text-green-500" />
                    ) : (
                      <XCircle className="size-5 text-destructive" />
                    )}
                  </div>
                )}
              </div>
              
              {/* URL Examples */}
              {url === "" && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Ejemplos de URLs válidas:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "https://docs.python.org/3/tutorial/",
                      "https://developer.mozilla.org/en-US/docs/Web",
                      "https://github.com/readme"
                    ].map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => setUrl(example)}
                        className="text-xs px-2 py-1 rounded-md bg-muted/50 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground flex items-center gap-1"
                      >
                        <ChevronRight className="size-3" />
                        {new URL(example).hostname}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Button
              className="w-full"
              onClick={handleIngestJob}
              disabled={loading || !isValidUrl}
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Globe className="size-4" />
                  Ingerir URL
                </>
              )}
            </Button>
          </TabsContent>

          {/* PDF Tab */}
          <TabsContent value="pdf" className="space-y-4 mt-4">
            {/* Large Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "relative rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200",
                isDragging
                  ? "border-primary bg-primary/5 scale-[1.02]"
                  : file
                  ? "border-green-500/50 bg-green-500/5"
                  : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30",
                loading && "opacity-50 pointer-events-none"
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setFile(e.target.files[0]);
                  }
                }}
                className="hidden"
                disabled={loading}
              />
              
              <div className="flex flex-col items-center gap-3">
                <div className={cn(
                  "p-4 rounded-full transition-colors",
                  file ? "bg-green-500/10" : "bg-primary/10"
                )}>
                  {file ? (
                    <FileText className="size-8 text-green-500" />
                  ) : (
                    <FileUp className="size-8 text-primary" />
                  )}
                </div>
                
                {file ? (
                  <div className="space-y-1">
                    <p className="font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                      className="text-xs text-destructive hover:underline"
                    >
                      Eliminar
                    </button>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="font-medium">
                      Arrastrá tu PDF aquí
                    </p>
                    <p className="text-xs text-muted-foreground">
                      o hacé clic para seleccionar
                    </p>
                  </div>
                )}
              </div>
            </div>

            <Button
              className="w-full"
              onClick={handleIngestPDFJob}
              disabled={loading || !file}
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Upload className="size-4" />
                  Subir PDF
                </>
              )}
            </Button>
          </TabsContent>
        </Tabs>
      </div>

      {/* Metadata Fields */}
      <CardContent className="pt-4 px-4">
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground font-medium">Metadatos (opcional)</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="domain" className="text-xs">Dominio</Label>
              <Input
                id="domain"
                placeholder="ej: tecnología"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="topic" className="text-xs">Tema</Label>
              <Input
                id="topic"
                placeholder="ej: documentación"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>
        </div>
      </CardContent>

      {/* Progress Section */}
      {loading && (
        <CardContent className="px-4 pb-4 animate-in slide-in-from-bottom-4 fade-in duration-300">
          <div className="rounded-lg bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {progress === 100 ? (
                  <CheckCircle2 className="size-4 text-green-500" />
                ) : (
                  <Loader2 className="size-4 animate-spin text-primary" />
                )}
                <span className="text-sm font-medium">
                  {progress === 100 ? "Completado" : statusMessage || "Procesando..."}
                </span>
              </div>
              <span className="text-sm text-muted-foreground">{progress}%</span>
            </div>
            <Progress 
              value={progress} 
              className="h-2"
            />
          </div>
        </CardContent>
      )}

      {/* Success State */}
      {progress === 100 && !loading && (
        <CardContent className="px-4 pb-4 animate-in slide-in-from-bottom-4 fade-in duration-300">
          <div className="rounded-lg bg-green-500/10 border border-green-500/20 p-4">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle2 className="size-5" />
              <span className="text-sm font-medium">¡Documento ingestado!</span>
            </div>
          </div>
        </CardContent>
      )}
    </div>
  );
}

export default IngestionInterface;
