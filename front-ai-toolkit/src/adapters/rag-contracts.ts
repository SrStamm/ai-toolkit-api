import type {
  JobStatusResponse,
  RagPath,
  SearchResponse,
  IngestRequest,
  IngestJobResponse as WireInjestJobResponse,
} from "@ai-toolkit/rag-contracts";

export const RAG_PATHS = {
  ingestJob: "/rag/ingest/job",
  ingestFileJob: "/rag/ingest-file/job",
  jobStatus: "/rag/job/{job_id}",
} as const satisfies Record<string, RagPath>;

/** Accept both an origin and the legacy `.../rag` value used in current .env files. */
export function toOriginBaseUrl(url: string): string {
  return url.replace(/\/rag\/?$/, "").replace(/\/$/, "");
}

export type RagCitation = SearchResponse["citations"][number];
export type FrontendJobStatus = "pending" | "running" | "completed" | "failed";

export interface IngestUrlInput {
  url: string;
  domain?: string;
  topic?: string;
}

export interface JobStatusView {
  jobId: string;
  status: FrontendJobStatus;
  progress: number | null;
  step: string;
  error?: string;
}

export function toWireIngestUrl(input: IngestUrlInput): IngestRequest {
  return {
    url: input.url,
    domain: input.domain ?? "general",
    topic: input.topic ?? "unknown",
  };
}

export function fromJobStatusResponse(payload: unknown): JobStatusView {
  const wire = payload as JobStatusResponse;
  return {
    jobId: wire.job_id,
    status: wire.status == "queued" ? "pending" : wire.status,
    progress: wire.progress ?? null,
    step: wire.step,
    error: wire.error ?? undefined,
  };
}

export function fromIngestJobResponse(payload: unknown): IngestJobStarted {
  const wire = payload as WireInjestJobResponse;
  return { status: "pending", jobId: wire.job_id };
}

export type IngestJobStarted = {
  status: FrontendJobStatus;
  jobId: string;
};
