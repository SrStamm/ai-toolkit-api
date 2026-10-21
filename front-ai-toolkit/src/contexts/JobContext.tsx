import { createContext, useContext } from "react";

export type JobSource = "ingestion-ui" | "agent-chat";
export type JobType = "job"; // Unified: backend now uses same format for all tasks

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

export interface JobContextType {
  jobs: Job[];
  activeJobs: Job[];
  addJob: (job: Omit<Job, "createdAt">) => void;
  updateJob: (id: string, updates: Partial<Job>) => void;
  removeJob: (id: string) => void;
}

export const JobContext = createContext<JobContextType | undefined>(undefined);

export function useJobContext() {
  const context = useContext(JobContext);
  if (context === undefined) {
    throw new Error("useJobContext must be used within a JobProvider");
  }
  return context;
}
