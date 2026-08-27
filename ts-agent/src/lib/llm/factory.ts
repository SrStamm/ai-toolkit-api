import { LLMInterface } from "./client";
import { MistralProvider } from "./providers/mistral";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing env var: ${name}`);
  return value;
}

export function getLlmProvider(): LLMInterface {
  return new MistralProvider(
    "https://api.mistral.ai/v1",
    requireEnv("MISTRAL_API_KEY"),
    "mistral-small-latest",
    0.5,
  );
}
