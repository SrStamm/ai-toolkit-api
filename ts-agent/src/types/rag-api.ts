/**
 * Agent-owned RAG models.
 *
 * These types describe what the agent's tools consume. They are deliberately
 * separate from the generated HTTP contract: conversions live in
 * `src/adapters/rag-contracts.ts`.
 */

export type Citation = string;

export interface SearchResult {
  context: string;
  citations: Citation[];
}

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

export interface IngestJobResponse {
  status: "queued";
  job_id: string;
}

export interface DeleteDocumentResponse {
  status: "deleted";
  source: string;
}

export interface SourceMetadata {
  source: string;
  display_name?: string | null;
  domain: string;
  topic: string;
  chunk_count: number;
  last_ingested: number;
}

export type ListDocumentsResponse = {
  status: "success";
  metadata: {
    documents: SourceMetadata[];
    count: number;
  };
  output: string;
};

export type DocumentMetadataResponse = {
  status: "success";
  metadata: SourceMetadata;
  output: string;
};
