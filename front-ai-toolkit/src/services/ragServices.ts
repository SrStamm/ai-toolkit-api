import type { IngestFile, Ingestrequest, QueryRequest } from "@/types/rag";
import Fetch from "@/utils/api";

const url = import.meta.env.VITE_URL;

export const ingestURLFetch = async (body: Ingestrequest) => {
  return await Fetch({ path: "/rag/ingest", method: "POST", body: body });
};

export const ingestURLStream = async (body: Ingestrequest) => {
  const response = await fetch(url + "/rag/ingest-stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response;
};

export const askFetch = async (body: QueryRequest) => {
  return await Fetch({ path: "/rag/ask", method: "POST", body: body });
};

export const askStreamFetch = async (body: QueryRequest): Promise<Response> => {
  const response = await fetch(url + "/rag/ask-stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response;
};

export const ingestFile = async (body: FormData) => {
  return await fetch(url + "/rag/ingest-pdf-stream", {
    method: "POST",
    body: body,
  });
};

export const getJobStatus = async (jobId: string) => {
  return await Fetch({ path: `/rag/job/${jobId}`, method: "GET" });
};

export const ingestURLJob = async (body: Ingestrequest) => {
  return await Fetch({ path: "/rag/ingest/job", method: "POST", body: body });
};

export const ingestFileJob = async (body: FormData) => {
  return await fetch(url + "/rag/ingest-file/job", {
    method: "POST",
    body: body,
  });
};
