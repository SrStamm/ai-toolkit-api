import { LLMInterface } from "./client";
import { MistralProvider } from "./providers/mistral";
import { GroqProvider } from "./providers/groq";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing env var: ${name}`);
  return value;
}

export function getLlmProvider(): LLMInterface {
  const provider = process.env.LLM_PROVIDER || "groq";

  switch (provider) {
    case "groq":
      return new GroqProvider(
        "https://api.groq.com/openai/v1",
        requireEnv("GROQ_API_KEY"),
        process.env.LLM_MODEL || "llama-3.3-70b-versatile",
        0.5,
      );
    case "mistral":
      return new MistralProvider(
        "https://api.mistral.ai/v1",
        requireEnv("MISTRAL_API_KEY"),
        process.env.LLM_MODEL || "mistral-small-latest",
        0.5,
      );
    default:
      throw new Error(`Unknown LLM_PROVIDER: ${provider}`);
  }
}
