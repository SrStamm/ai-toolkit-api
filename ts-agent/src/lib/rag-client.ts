import {
  DeleteDocumentResponse,
  DocumentMetadataResponse,
  IngestData,
  IngestJobResponse,
  ListDocumentsResponse,
  SearchOptions,
  SearchResult,
} from "../types/rag-api";
import {
  fromDeleteDocumentResponse,
  fromDocumentMetadataResponse,
  fromIngestJobResponse,
  fromListDocumentsResponse,
  fromSearchResponse,
  RAG_PATHS,
  toOriginBaseUrl,
  toWireIngest,
  toWireSearch,
} from "../adapters/rag-contracts";
import { logger } from "./logger";
import { HttpToolError, toCodeError } from "../types/tool-error";

const log = logger.child("rag-client");

export interface RagClient {
  search(
    query: string,
    opts: SearchOptions,
    signal?: AbortSignal,
  ): Promise<SearchResult>;
  ingest(data: IngestData, signal?: AbortSignal): Promise<IngestJobResponse>;
  deleteDocument(
    source: string,
    signal?: AbortSignal,
  ): Promise<DeleteDocumentResponse>;
  getSourceMetadata(
    source: string,
    signal?: AbortSignal,
  ): Promise<DocumentMetadataResponse>;
  listSources(
    domain?: string,
    signal?: AbortSignal,
  ): Promise<ListDocumentsResponse>;
}

class HTTPRagClient implements RagClient {
  constructor(private baseUrl: string) {}

  async search(
    query: string,
    opts: SearchOptions,
    signal?: AbortSignal,
  ): Promise<SearchResult> {
    log.debug("search_start", {
      query_preview: query.slice(0, 80),
      top_k: opts.topK,
      domain: opts.domain,
    });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}${RAG_PATHS.search}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toWireSearch(query, opts)),
      signal,
    });

    if (!response.ok) {
      const code = toCodeError(response);
      log.error("search_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new HttpToolError(
        response.status,
        code,
        `RAG request failed (${response.status})`,
      );
    }

    const result = fromSearchResponse(await response.json());

    log.info("search_completed", {
      duration_ms: Date.now() - startTime,
      has_context: !!result.context,
      citation_count: result.citations?.length ?? 0,
    });

    return result;
  }

  async ingest(
    data: IngestData,
    signal?: AbortSignal,
  ): Promise<IngestJobResponse> {
    log.debug("ingest_start", {
      url: data.url,
      domain: data.domain,
    });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}${RAG_PATHS.ingestJob}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toWireIngest(data)),
      signal,
    });

    if (!response.ok) {
      const code = toCodeError(response);
      log.error("ingest_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new HttpToolError(
        response.status,
        code,
        `RAG request failed (${response.status})`,
      );
    }

    const result = fromIngestJobResponse(await response.json());

    log.info("ingest_completed", {
      duration_ms: Date.now() - startTime,
      job_id: result.job_id,
    });

    return result;
  }

  async deleteDocument(
    source: string,
    signal?: AbortSignal,
  ): Promise<DeleteDocumentResponse> {
    log.debug("delete_start", { source });

    const startTime = Date.now();

    const path = RAG_PATHS.document.replace(
      "{source}",
      encodeURIComponent(source),
    );
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      signal,
    });

    if (!response.ok) {
      const code = toCodeError(response);
      log.error("delete_failed", {
        source,
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new HttpToolError(
        response.status,
        code,
        `RAG request failed (${response.status})`,
      );
    }

    const result = fromDeleteDocumentResponse(await response.json());

    log.info("delete_completed", {
      source,
      duration_ms: Date.now() - startTime,
    });

    return result;
  }

  async listSources(
    domain?: string,
    signal?: AbortSignal,
  ): Promise<ListDocumentsResponse> {
    log.debug("list_sources_start", { domain });

    const startTime = Date.now();

    const response = await fetch(`${this.baseUrl}${RAG_PATHS.documents}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
      signal,
    });

    if (!response.ok) {
      const code = toCodeError(response);
      log.error("list_sources_failed", {
        status: response.status,
        duration_ms: Date.now() - startTime,
      });
      throw new HttpToolError(
        response.status,
        code,
        `RAG request failed (${response.status})`,
      );
    }

    const result = fromListDocumentsResponse(await response.json());

    log.info("list_sources_completed", {
      duration_ms: Date.now() - startTime,
      status: result.status,
      document_count: result.metadata.count,
    });

    return result;
  }

  async getSourceMetadata(
    source: string,
    signal?: AbortSignal,
  ): Promise<DocumentMetadataResponse> {
    log.debug("get_metadata_start", { source });

    const startTime = Date.now();

    const response = await fetch(
      `${this.baseUrl}${RAG_PATHS.metadata}?source=${encodeURIComponent(source)}`,
      {
        method: "GET",
        signal,
      },
    );

    if (!response.ok) {
      const code = toCodeError(response);

      log.error("get_metadata_failed", {
        source,
        status: response.status,
        duration_ms: Date.now() - startTime,
      });

      throw new HttpToolError(
        response.status,
        code,
        `RAG request failed (${response.status})`,
      );
    }

    const result = fromDocumentMetadataResponse(await response.json());

    log.info("get_metadata_completed", {
      source,
      duration_ms: Date.now() - startTime,
      status: result.status,
    });

    return result;
  }
}

export const httpClient = new HTTPRagClient(
  toOriginBaseUrl(process.env.RAG_URL || "http://localhost:8000"),
);
