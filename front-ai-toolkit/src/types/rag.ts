export interface Ingestrequest {
  url: string;
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
