import {
  fromIngestJobResponse,
  fromJobStatusResponse,
  RAG_PATHS,
  toWireIngestUrl,
  type IngestJobStarted,
  type IngestUrlInput,
  type JobStatusView,
} from "../adapters/rag-contracts";
import Fetch from "@/utils/api";

export const getJobStatus = async (jobId: string): Promise<JobStatusView> => {
  const resp = await Fetch<unknown>({
    path: RAG_PATHS.jobStatus.replace("{job_id}", jobId),
    method: "GET",
  });
  return fromJobStatusResponse(resp);
};

export const ingestURLJob = async (
  body: IngestUrlInput,
): Promise<IngestJobStarted> => {
  const wire = toWireIngestUrl(body);
  const resp = await Fetch<unknown>({
    path: RAG_PATHS.ingestJob,
    method: "POST",
    body: wire,
  });
  return fromIngestJobResponse(resp);
};

export const ingestFileJob = async (
  body: FormData,
): Promise<IngestJobStarted> => {
  const response = await fetch(RAG_PATHS.ingestFileJob, {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error(`Ingest File Job failed: ${response.status}`);
  }
  return fromIngestJobResponse(await response.json());
};
