import { readFileSync } from "node:fs";
import { join } from "node:path";
import yaml from "js-yaml";
import type { AppConfig, ProviderConfig, ModelConfig } from "../types/provider";

// --- Raw YAML shapes (snake_case as written in the file) ---

interface RawModelConfig {
  name: string;
  max_tokens: number;
  supports_tools: boolean;
}

interface RawProviderConfig {
  name: string;
  api_key_env: string;
  default_model?: string;
  models: RawModelConfig[];
}

interface RawAppConfig {
  providers: RawProviderConfig[];
}

// --- Mappers ---

function mapModel(raw: RawModelConfig): ModelConfig {
  return {
    name: raw.name,
    maxTokens: raw.max_tokens,
    supportsTools: raw.supports_tools,
  };
}

function mapProvider(raw: RawProviderConfig): ProviderConfig {
  return {
    name: raw.name,
    apiKeyEnv: raw.api_key_env,
    defaultModel: raw.default_model,
    models: raw.models.map(mapModel),
  };
}

// --- Loader ---

export function loadProvidersConfig(configPath?: string): AppConfig {
  const resolvedPath =
    configPath ?? join(__dirname, "providers.yaml");

  const file = readFileSync(resolvedPath, "utf-8");
  const raw = yaml.load(file) as RawAppConfig;

  if (!raw?.providers || !Array.isArray(raw.providers)) {
    throw new Error("Invalid providers.yaml: missing 'providers' array");
  }

  return {
    providers: raw.providers.map(mapProvider),
  };
}
