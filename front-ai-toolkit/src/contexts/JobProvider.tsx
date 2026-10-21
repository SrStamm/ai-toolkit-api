import {
  useState,
  useCallback,
  type ReactNode,
  useEffect,
  useRef,
} from "react";
import { getJobStatus } from "@/services/ragServices";
import { showToastError, showToastSuccess } from "@/components/toast";
import { JobContext, type Job, type JobContextType } from "@/contexts/JobContext";

// Auto-cleanup time for completed jobs (5 seconds)
const AUTO_CLEAN_UP_DELAY = 5000;

export function JobProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  // Current time snapshot, refreshed by the auto-cleanup interval. Holding it
  // in state keeps the render phase pure (no `Date.now()` during render).
  const [now, setNow] = useState(0);
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
      const timestamp = Date.now();
      setNow(timestamp);
      setJobs((prev) =>
        prev.filter(
          (job) =>
            !job.completedAt ||
            timestamp - job.completedAt < AUTO_CLEAN_UP_DELAY,
        ),
      );
    }, AUTO_CLEAN_UP_DELAY);

    return () => clearInterval(timer);
  }, []);

  // Auto-start polling when job is added
  useEffect(() => {
    // Capture the map instance so the cleanup closes over the same one
    const refs = pollingRefs.current;

    jobs.forEach((job) => {
      // Skip if already polling or job is done
      if (refs.has(job.id)) return;
      if (job.completedAt) return;

      // Unified polling: all jobs use same backend format
      const poll = async () => {
        try {
          const data = await getJobStatus(job.id);

          const nextMessage =
            data.status === "completed"
              ? "¡Completado!"
              : data.status === "failed"
                ? "Error"
                : data.step || "Procesando...";

          updateJob(job.id, {
            status: data.status,
            progress: data.progress || 0,
            message: nextMessage,
            ...(data.status === "failed" ? { error: data.error } : {}),
          });

          if (data.status === "completed") {
            showToastSuccess(
              job.source === "agent-chat"
                ? "Tarea completada con éxito"
                : "¡Ingesta completada con éxito!",
            );
          } else if (data.status === "failed") {
            showToastError(`Error: ${data.error || "Desconocido"}`);
          }
        } catch (error) {
          console.error("Polling error:", error);
        }
      };

      poll(); // Initial poll
      const intervalId = window.setInterval(poll, 2000);
      refs.set(job.id, intervalId);
    });

    // Cleanup intervals for completed jobs
    return () => {
      jobs.forEach((job) => {
        if (job.completedAt && refs.has(job.id)) {
          const intervalId = refs.get(job.id);
          if (intervalId) {
            clearInterval(intervalId);
          }
          refs.delete(job.id);
        }
      });
    };
  }, [jobs, updateJob]);

  const activeJobs = jobs.filter(
    (job) =>
      !job.completedAt ||
      (job.completedAt && now - job.completedAt < AUTO_CLEAN_UP_DELAY),
  );

  const contextValue: JobContextType = {
    jobs,
    activeJobs,
    addJob,
    updateJob,
    removeJob,
  };

  return (
    <JobContext.Provider value={contextValue}>
      {children}
    </JobContext.Provider>
  );
}
