// Mistral provider
import { LLMResponse, Message } from "../../../types/llm";
import { LLMInterface } from "../client";
import { configDotenv } from "dotenv";

configDotenv();

interface MistralUsage {
  prompt_tokens: number;
  total_tokens: number;
  completion_tokens: number;
}

interface MistralMessage {
  role: string;
  content: string;
}

interface MistralChoice {
  index: number;
  finish_reason: string;
  message: MistralMessage;
}

interface MistralResponse {
  model: string;
  usage: MistralUsage;
  choices: MistralChoice[];
}

export class MistralProvider implements LLMInterface {
  private endpoint: string;

  constructor(
    private baseUrl: string,
    private apiKey: string,
    private model: string,
    private temperature: number,
  ) {
    this.endpoint = `${this.baseUrl}/chat/completions`;
  }

  async chat(messages: Message[], systemPrompt: string): Promise<LLMResponse> {
    messages = [{ role: "system", content: systemPrompt }, ...messages];

    // Request data
    const data = {
      model: this.model,
      messages: messages,
      temperature: this.temperature,
      response_format: { type: "json_object" },
    };

    const response = await fetch(this.endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`LLM client failed: ${response.status}`);
    }

    const raw = (await response.json()) as MistralResponse;

    return {
      content: raw.choices[0].message.content,
      usage: {
        prompt_tokens: raw.usage.prompt_tokens,
        completion_tokens: raw.usage.completion_tokens,
        total_tokens: raw.usage.total_tokens,
      },
      cost: { input_cost: 0, output_cost: 0, total_cost: 0 },
      model: raw.model,
      provider: "mistral",
    };
  }
}
