export interface Citation {
  source: string;
  chunk_index: number;
  text: string;
}

export interface SearchResult {
  context: string;
  citations: Citation[];
}

export type ListDocumentsResponse =
  | {
      status: "success";
      metadata: {
        documents: SourceMetadata[];
        count: number;
      };
      output: string;
    }
  | { status: "failed" };

export interface DeleteDocumentResponse {
  status: "deleted";
  source: string;
}

export type DocumentMetadataResponse =
  | { status: "success"; metadata: SourceMetadata; output: string }
  | { status: "failed" };

export interface SearchOptions {
  topK?: number;
  domain: string;
  topic?: string;
}

export interface IngestData {
  url: string;
  source: string;
  domain: string;
  topic: string;
}

export interface IngestResult {
  chunksProcessed: number;
  new: number;
  updated: number;
}

export interface IngestJobResult {
  status: "queued" | "processing" | "completed" | "failed";
  jobId: string;
}

export interface SourceMetadata {
  source: string;
  domain: string;
  topic: string;
  chunkCount: number;
  lastIngested: number;
}

export interface JobState {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  step: string;
  error?: string;
}
