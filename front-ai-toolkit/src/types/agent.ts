export interface AgentQuestion {
  text: string;
  session_id?: string;
  file_uuid?: string;
  filename?: string;
}

export interface AgentResponse {
  output: string;
  session_id: string;
  metadata: Record<string, unknown>;
}
