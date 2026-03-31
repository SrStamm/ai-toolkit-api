export interface Ingestrequest {
  url: string;
  domain?: string;
  topic?: string;
}

export interface IngestFile {
  file: File;
  domain?: string;
  topic?: string;
}

export interface QueryRequest {
  text: string;
  domain?: string;
  topic?: string;
}

export interface Citation {
  source: string;
  chunk_index: number;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
}

export interface JobStatusResponse {
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  step?: string;
  error?: string;
}

export interface JobResponse {
  job_id: string;
}
