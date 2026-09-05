export interface AgentQuestion {
  query: string;
  sessionId?: string;
  file_uuid?: string;
  filename?: string;
}

export interface AgentResponse {
  output: string;
  sessionId: string;
  metadata: Record<string, unknown>;
}
