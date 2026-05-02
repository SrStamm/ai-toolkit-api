import { useJobContext } from "@/contexts/JobContext";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export function ActiveJobsPanel() {
  const { activeJobs, removeJob } = useJobContext();

  if (activeJobs.length === 0) return null;

  return (
    <div className="px-4 pb-4 space-y-3 animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground font-medium">Tareas activas</p>
        <button
          onClick={() =>
            activeJobs.forEach((j) => {
              if (
                j.completedAt ||
                j.status === "SUCCESS" ||
                j.status === "FAILURE" ||
                j.status === "completed" ||
                j.status === "failed"
              ) {
                removeJob(j.id);
              }
            })
          }
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Limpiar completadas
        </button>
      </div>

      {activeJobs.map((job) => (
        <div key={job.id} className="rounded-lg bg-muted/30 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {job.status === "completed" || job.status === "SUCCESS" ? (
                <CheckCircle2 className="size-4 text-green-500" />
              ) : job.status === "failed" || job.status === "FAILURE" ? (
                <XCircle className="size-4 text-destructive" />
              ) : (
                <Loader2 className="size-4 animate-spin text-primary" />
              )}
              <span className="text-sm font-medium">
                {job.message || job.status}
                {job.source === "agent-chat" && (
                  <span className="ml-2 text-xs bg-blue-500/10 text-blue-600 px-1.5 py-0.5 rounded">
                    Agente
                  </span>
                )}
              </span>
            </div>
            <span className="text-sm text-muted-foreground">{job.progress}%</span>
          </div>
          <Progress
            value={job.progress}
            className={cn("h-2", {
              "[&_[data-slot=progress-indicator]]:bg-destructive]":
                job.status === "failed" || job.status === "FAILURE",
            })}
          />
          {job.error && <p className="text-xs text-destructive">{job.error}</p>}
        </div>
      ))}
    </div>
  );
}
