import {
  IngestData,
  IngestResult,
  SearchOptions,
  SearchResult,
  SourceMetadata,
} from "../types/rag-api";

export interface RagClient {
  search(query: string, opts: SearchOptions): Promise<SearchResult>;
  ingest(data: IngestData): Promise<IngestResult>;
  deleteDocument(source: string): Promise<void>;
  getSourceMetadata(source: string): Promise<SourceMetadata | null>;
  listSources(domain?: string): Promise<SourceMetadata[]>;
}

class HTTPRagClient implements RagClient {
  constructor(private baseUrl: string) {}

  async search(query: string, opts: SearchOptions) {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        domain: opts.domain,
        top_k: opts.topK ?? 5,
      }),
    });

    if (!response.ok) {
      throw new Error(`RAG search failed: ${response.status}`);
    }

    return response.json();
  }
}

async function test() {
  const client = new HTTPRagClient("http://localhost:8000/rag");
  const data = await client.search("Como funciona Merge en Docker?", {
    domain: "Docker",
  });
  console.log(data);
}

test();
