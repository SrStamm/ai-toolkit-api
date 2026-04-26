export interface LLMProvider {
  name: string;
  default_model: string;
  models: LLMModel[];
}

export interface LLMModel {
  name: string;
  max_tokens: number;
  supports_tools: boolean;
}

export interface LLMConfigResponse {
  providers: LLMProvider[];
}

export interface LLMConfig {
  provider: string;
  model: string;
}