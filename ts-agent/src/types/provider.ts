export interface ModelConfig {
  name: string;
  maxTokens: number;
  supportsTools: boolean;
}

export interface ProviderConfig {
  name: string;
  apiKeyEnv: string;
  defaultModel?: string;
  models: ModelConfig[];
}

export interface AppConfig {
  providers: ProviderConfig[];
}
