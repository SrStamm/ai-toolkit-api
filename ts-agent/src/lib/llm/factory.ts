import { LLMInterface } from "./client";
import { MistralProvider } from "./providers/mistral";
import { GroqProvider } from "./providers/groq";
import { loadProvidersConfig } from "../../config/loader";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing env var: ${name}`);
  return value;
}

/**
 * Resolve the API key for a provider.
 * Env vars follow the convention: <PROVIDER>_API_KEY (e.g. GROQ_API_KEY, MISTRAL_API_KEY).
 * Providers with an empty api_key_env (like Ollama) return an empty string.
 */
function resolveApiKey(providerName: string, apiKeyEnv: string): string {
  if (!apiKeyEnv) return "";
  return requireEnv(apiKeyEnv);
}

interface LlmOverrides {
  provider?: string;
  model?: string;
}

export function getLlmProvider(overrides?: LlmOverrides): LLMInterface {
  const config = loadProvidersConfig();

  const providerName =
    overrides?.provider || process.env.LLM_PROVIDER || "groq";
  const modelOverride = overrides?.model;

  // Find the provider in config
  const providerConfig = config.providers.find(
    (p) => p.name === providerName,
  );
  if (!providerConfig) {
    const available = config.providers.map((p) => p.name).join(", ");
    throw new Error(
      `Unknown provider '${providerName}'. Available: [${available}]`,
    );
  }

  // Resolve model: header override > env var > config default
  const model =
    modelOverride || process.env.LLM_MODEL || providerConfig.defaultModel;
  if (!model) {
    throw new Error(
      `No model specified for provider '${providerName}' and no default_model configured`,
    );
  }

  // Validate model exists in provider config
  const modelConfig = providerConfig.models.find((m) => m.name === model);
  if (!modelConfig) {
    const available = providerConfig.models.map((m) => m.name).join(", ");
    throw new Error(
      `Model '${model}' not found for provider '${providerName}'. Available: [${available}]`,
    );
  }

  const apiKey = resolveApiKey(providerName, providerConfig.apiKeyEnv);

  switch (providerName) {
    case "groq":
      return new GroqProvider(
        "https://api.groq.com/openai/v1",
        apiKey,
        model,
        0.5,
      );
    case "mistral":
      return new MistralProvider(
        "https://api.mistral.ai/v1",
        apiKey,
        model,
        0.5,
      );
    default:
      throw new Error(
        `Provider '${providerName}' has no LLM implementation in ts-agent. Available: [groq, mistral]`,
      );
  }
}
