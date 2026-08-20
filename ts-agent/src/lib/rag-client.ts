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

  async ingest(data: IngestData) {
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
      throw new Error(`Ingest File Job failed: ${response.status}`);
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

  const data2 = await client.ingest({
    url: "https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/",
    source: "Docker",
    domain: "Docker",
    topic: "Merge",
  });

  console.log(data2);
}

test();
