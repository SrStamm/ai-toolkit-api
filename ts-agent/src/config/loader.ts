import { readFileSync } from "node:fs";
import { join } from "node:path";
import yaml from "js-yaml";
import type { AppConfig, ProviderConfig, ModelConfig } from "../types/provider";
import { logger } from "../lib/logger";

const log = logger.child("config");

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

  log.debug("loading_config", { path: resolvedPath });

  const file = readFileSync(resolvedPath, "utf-8");
  const raw = yaml.load(file) as RawAppConfig;

  if (!raw?.providers || !Array.isArray(raw.providers)) {
    log.error("config_invalid", { reason: "missing providers array" });
    throw new Error("Invalid providers.yaml: missing 'providers' array");
  }

  const config = {
    providers: raw.providers.map(mapProvider),
  };

  log.info("config_loaded", {
    provider_count: config.providers.length,
    providers: config.providers.map((p) => p.name),
  });

  return config;
}
