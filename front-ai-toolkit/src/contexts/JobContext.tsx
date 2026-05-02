import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
  useEffect,
  useRef,
} from "react";
import { getJobStatus } from "@/services/ragServices";
import { showToastError, showToastSuccess } from "@/components/toast";

const baseUrl = import.meta.env.VITE_URL || "";

// Auto-cleanup time for completed jobs (5 seconds)
const AUTO_CLEAN_UP_DELAY = 5000;

export type JobSource = "ingestion-ui" | "agent-chat";
export type JobType = "ingestion-job" | "celery-task";

export interface Job {
  id: string;
  type: JobType;
  source: JobSource;
  status: string;
  progress: number;
  message?: string;
  error?: string;
  createdAt: number;
  completedAt?: number;
}

interface JobContextType {
  jobs: Job[];
  activeJobs: Job[];
  addJob: (job: Omit<Job, "createdAt">) => void;
  updateJob: (id: string, updates: Partial<Job>) => void;
  removeJob: (id: string) => void;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

export function JobProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const pollingRefs = useRef<Map<string, number>>(new Map());

  const addJob = useCallback((job: Omit<Job, "createdAt">) => {
    setJobs((prev) => [
      ...prev.filter((j) => j.id !== job.id),
      { ...job, createdAt: Date.now() },
    ]);
  }, []);

  const updateJob = useCallback((id: string, updates: Partial<Job>) => {
    setJobs((prev) =>
      prev.map((job) =>
        job.id === id
          ? {
              ...job,
              ...updates,
              ...(updates.status === "completed" ||
              updates.status === "SUCCESS" ||
              updates.status === "failed" ||
              updates.status === "FAILURE"
                ? { completedAt: Date.now() }
                : {}),
            }
          : job,
      ),
    );
  }, []);

  const removeJob = useCallback((id: string) => {
    pollingRefs.current.delete(id);
    setJobs((prev) => prev.filter((job) => job.id !== id));
  }, []);

  // Auto-cleanup completed jobs after delay
  useEffect(() => {
    const timer = setInterval(() => {
      setJobs((prev) =>
        prev.filter(
          (job) =>
            !job.completedAt ||
            Date.now() - job.completedAt < AUTO_CLEAN_UP_DELAY,
        ),
      );
    }, AUTO_CLEAN_UP_DELAY);

    return () => clearInterval(timer);
  }, []);

  // Auto-start polling when job is added
  useEffect(() => {
    jobs.forEach((job) => {
      // Skip if already polling or job is done
      if (pollingRefs.current.has(job.id)) return;
      if (job.completedAt) return;

      // Start polling based on job type
      if (job.type === "ingestion-job") {
        const poll = async () => {
          try {
            const data = await getJobStatus(job.id);
            updateJob(job.id, {
              status: data.status,
              progress: data.progress,
              message:
                data.status === "completed"
                  ? "¡Completado!"
                  : data.step || "Procesando...",
              ...(data.status === "failed" ? { error: data.error } : {}),
            });

            if (data.status === "completed") {
              showToastSuccess("¡Ingesta completada con éxito!");
            } else if (data.status === "failed") {
              showToastError(`Error: ${data.error || "Desconocido"}`);
            }
          } catch (error) {
            console.error("Polling error:", error);
          }
        };

        poll(); // Initial poll
        const intervalId = window.setInterval(poll, 2000);
        pollingRefs.current.set(job.id, intervalId);
      } else if (job.type === "celery-task") {
        const pollCelery = async () => {
          try {
            const response = await fetch(`${baseUrl}/rag/job/${job.id}`);
            if (!response.ok)
              throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            if (data.celery_state) {
              updateJob(job.id, {
                status: data.celery_state,
                message: `Task ${job.id}: ${data.celery_state}`,
              });

              if (
                ["SUCCESS", "FAILURE", "REVOKED"].includes(data.celery_state)
              ) {
                if (data.celery_state === "SUCCESS") {
                  updateJob(job.id, { progress: 100, message: "Completed" });
                  showToastSuccess("Tarea completada");
                } else {
                  updateJob(job.id, { error: data.error || "Task failed" });
                  showToastError(`Error: ${data.error || "Task failed"}`);
                }
              }
            } else if (data.status) {
              updateJob(job.id, {
                status: data.status,
                message: `Task ${job.id}: ${data.status}`,
              });
            }
          } catch (err) {
            const msg = err instanceof Error ? err.message : "Polling error";
            updateJob(job.id, { status: "FAILURE", error: msg });
            showToastError(`Error: ${msg}`);
          }
        };

        pollCelery(); // Initial poll
        const intervalId = window.setInterval(pollCelery, 3000);
        pollingRefs.current.set(job.id, intervalId);
      }
    });

    // Cleanup intervals for completed jobs
    return () => {
      jobs.forEach((job) => {
        if (job.completedAt && pollingRefs.current.has(job.id)) {
          const intervalId = pollingRefs.current.get(job.id);
          if (intervalId && intervalId !== -1) {
            clearInterval(intervalId);
          }
          pollingRefs.current.delete(job.id);
        }
      });
    };
  }, [jobs, updateJob]);

  const activeJobs = jobs.filter(
    (job) =>
      !job.completedAt ||
      (job.completedAt && Date.now() - job.completedAt < 5000),
  );

  return (
    <JobContext.Provider
      value={{ jobs, activeJobs, addJob, updateJob, removeJob }}
    >
      {children}
    </JobContext.Provider>
  );
}

export function useJobContext() {
  const context = useContext(JobContext);
  if (context === undefined) {
    throw new Error("useJobContext must be used within a JobProvider");
  }
  return context;
}
