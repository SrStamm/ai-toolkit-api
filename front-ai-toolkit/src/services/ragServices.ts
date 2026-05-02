import type {
  Ingestrequest,
  JobStatusResponse,
  JobResponse,
} from "@/types/rag";
import Fetch from "@/utils/api";

const url = import.meta.env.VITE_URL;

export const getJobStatus = async (
  jobId: string,
): Promise<JobStatusResponse> => {
  return await Fetch<JobStatusResponse>({
    path: `/rag/job/${jobId}`,
    method: "GET",
  });
};

export const ingestURLJob = async (
  body: Ingestrequest,
): Promise<JobResponse> => {
  return await Fetch<JobResponse>({
    path: "/rag/ingest/job",
    method: "POST",
    body: body,
  });
};

export const ingestFileJob = async (body: FormData) => {
  return await fetch(url + "/rag/ingest-file/job", {
    method: "POST",
    body: body,
  });
};
