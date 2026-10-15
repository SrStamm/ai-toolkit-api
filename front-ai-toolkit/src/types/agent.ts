export interface AgentQuestion {
  query: string;
  sessionId?: string;
}

export interface AgentResponse {
  output: string;
  sessionId: string;
  metadata: Record<string, unknown>;
}
