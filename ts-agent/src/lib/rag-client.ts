import {
  DeleteDocumentResponse,
  DocumentMetadataResponse,
  IngestData,
  IngestResult,
  ListDocumentsResponse,
  SearchOptions,
  SearchResult,
  SourceMetadata,
} from "../types/rag-api";

export interface RagClient {
  search(query: string, opts: SearchOptions): Promise<SearchResult>;
  ingest(data: IngestData): Promise<IngestResult>;
  deleteDocument(source: string): Promise<DeleteDocumentResponse>;
  getSourceMetadata(source: string): Promise<DocumentMetadataResponse | null>;
  listSources(domain?: string): Promise<ListDocumentsResponse>;
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
        topic: opts.topic ?? null,
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

  async deleteDocument(source: string): Promise<DeleteDocumentResponse> {
    const response = await fetch(
      `${this.baseUrl}/documents/${encodeURIComponent(source)}`,
      {
        method: "DELETE",
      },
    );

    if (!response.ok) {
      throw new Error(`Delete Document failed: ${response.status}`);
    }

    return response.json();
  }

  async listSources(domain?: string): Promise<ListDocumentsResponse> {
    const response = await fetch(`${this.baseUrl}/documents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain }),
    });

    if (!response.ok) {
      throw new Error(`Get List Sources failed: ${response.status}`);
    }

    return response.json();
  }

  async getSourceMetadata(
    source: string,
  ): Promise<DocumentMetadataResponse | null> {
    const response = await fetch(
      `${this.baseUrl}/documents/metadata?source=${encodeURIComponent(source)}`,
      {
        method: "GET",
      },
    );

    if (!response.ok) {
      throw new Error(`Get Document Metadata failed: ${response.status}`);
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

  const data3 = await client.getSourceMetadata(
    "https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/",
  );

  console.log(data3);

  const data4 = await client.listSources("Docker");
  console.log(data4);

  // const data2 = await client.ingest({
  //   url: "https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/",
  //   source: "Docker",
  //   domain: "Docker",
  //   topic: "Merge",
  // });

  // console.log(data2);
}

test();

export const httpClient = new HTTPRagClient("http://localhost:8000/rag");
