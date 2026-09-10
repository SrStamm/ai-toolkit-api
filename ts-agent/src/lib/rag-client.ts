import {
  DeleteDocumentResponse,
  DocumentMetadataResponse,
  IngestData,
  IngestResult,
  ListDocumentsResponse,
  SearchOptions,
  SearchResult,
} from "../types/rag-api";
import { logger } from "./logger";

const log = logger.child("rag-client");

export interface RagClient {
  search(query: string, opts: SearchOptions): Promise<SearchResult>;
  ingest(data: IngestData): Promise<IngestResult>;
  deleteDocument(source: string): Promise<DeleteDocumentResponse>;
  getSourceMetadata(source: string): Promise<DocumentMetadataResponse>;
  listSources(domain?: string): Promise<ListDocumentsResponse>;
}

class HTTPRagClient implements RagClient {
  constructor(private baseUrl: string) {}

  async search(query: string, opts: SearchOptions) {
    log.debug("search_start", {
      query_preview: query.slice(0, 80),
      top_k: opts.topK,
      domain: opts.domain,
    });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        domain: opts.domain,
        topic: opts.topic ?? null,
        top_k: opts.topK ?? 5,
      }),
    });

    if (!response.ok) {
      log.error("search_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`RAG search failed: ${response.status}`);
    }

    const result = await response.json();

    log.info("search_completed", {
      duration_ms: Date.now() - startTime,
      has_context: !!result.context,
      citation_count: result.citations?.length ?? 0,
    });

    return result;
  }

  async ingest(data: IngestData) {
    log.debug("ingest_start", {
      url: data.url,
      domain: data.domain,
    });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}/ingest/job`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: data.url,
        domain: data.domain,
        topic: data.topic,
      }),
    });

    if (!response.ok) {
      log.error("ingest_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`Ingest File Job failed: ${response.status}`);
    }

    const result = await response.json();

    log.info("ingest_completed", {
      duration_ms: Date.now() - startTime,
      job_id: result.job_id,
    });

    return result;
  }

  async deleteDocument(source: string): Promise<DeleteDocumentResponse> {
    log.debug("delete_start", { source });

    const startTime = Date.now();

    const response = await fetch(
      `${this.baseUrl}/documents/${encodeURIComponent(source)}`,
      {
        method: "DELETE",
      },
    );

    if (!response.ok) {
      log.error("delete_failed", {
        source,
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`Delete Document failed: ${response.status}`);
    }

    const result = await response.json();

    log.info("delete_completed", {
      source,
      duration_ms: Date.now() - startTime,
    });

    return result;
  }

  async listSources(domain?: string): Promise<ListDocumentsResponse> {
    log.debug("list_sources_start", { domain });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}/documents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
    });

    if (!response.ok) {
      log.error("list_sources_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`Get List Sources failed: ${response.status}`);
    }

    const result = await response.json();

    log.info("list_sources_completed", {
      duration_ms: Date.now() - startTime,
      status: result.status,
      document_count: result.metadata?.count ?? 0,
    });

    return result;
  }

  async getSourceMetadata(source: string): Promise<DocumentMetadataResponse> {
    log.debug("get_metadata_start", { source });

    const startTime = Date.now();

    const response = await fetch(
      `${this.baseUrl}/documents/metadata?source=${encodeURIComponent(source)}`,
      {
        method: "GET",
      },
    );

    if (!response.ok) {
      log.error("get_metadata_failed", {
        source,
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`Get Document Metadata failed: ${response.status}`);
    }

    const result = await response.json();

    log.info("get_metadata_completed", {
      source,
      duration_ms: Date.now() - startTime,
      status: result.status,
    });

    return result;
  }
}

const RAG_URL = process.env.RAG_URL;

export const httpClient = new HTTPRagClient(
  RAG_URL || "http://localhost:8000/rag",
);
