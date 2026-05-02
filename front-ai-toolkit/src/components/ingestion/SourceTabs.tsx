import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { showToastError } from "@/components/toast";
import { ingestFileJob, ingestURLJob } from "@/services/ragServices";
import { useJobContext } from "@/contexts/JobContext";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  Globe,
  FileText,
  Upload,
  Link2,
  CheckCircle2,
  XCircle,
  FileUp,
  ChevronRight,
} from "lucide-react";

interface SourceTabsProps {
  loading: boolean;
  setLoading: (loading: boolean) => void;
  domain: string;
  topic: string;
}

export function SourceTabs({
  loading,
  setLoading,
  domain,
  topic,
}: SourceTabsProps) {
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { addJob } = useJobContext();

  const isValidUrl = url.startsWith("http://") || url.startsWith("https://");

  const handleIngestJob = async () => {
    if (!isValidUrl) return;
    setLoading(true);

    try {
      const response = await ingestURLJob({ url, domain, topic });
      if (response.job_id) {
        addJob({
          id: response.job_id,
          type: "job",
          source: "ingestion-ui",
          status: "pending",
          progress: 0,
          message: "Iniciando...",
        });
        setLoading(false);
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
        addJob({
          id: json.job_id,
          type: "job",
          source: "ingestion-ui",
          status: "pending",
          progress: 0,
          message: "Subiendo...",
        });
        setLoading(false);
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

  return (
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
                    "https://github.com/readme",
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
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
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
              <div
                className={cn(
                  "p-4 rounded-full transition-colors",
                  file ? "bg-green-500/10" : "bg-primary/10"
                )}
              >
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
                  <p className="font-medium">Arrastrá tu PDF aquí</p>
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
  );
}
