export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface CostBreakdown {
  input_cost: number;
  output_cost: number;
  total_cost: number;
  currency?: string;
}

export interface LLMResponse {
  content: string;
  usage: TokenUsage;
  cost: CostBreakdown;
  model: string;
  provider: string;
}

export type LLMStreamChunk = [string, LLMResponse | null];
