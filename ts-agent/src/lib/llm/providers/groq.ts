// Groq provider — OpenAI-compatible, no response_format support
import { LLMResponse, Message } from "../../../types/llm";
import { LLMInterface } from "../client";
import { logger } from "../../logger";

const log = logger.child("llm:groq");

interface GroqUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface GroqChoice {
  index: number;
  finish_reason: string;
  message: { role: string; content: string };
}

interface GroqResponse {
  model: string;
  usage: GroqUsage;
  choices: GroqChoice[];
}

export class GroqProvider implements LLMInterface {
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
    const data = {
      model: this.model,
      messages: [{ role: "system", content: systemPrompt }, ...messages],
      temperature: this.temperature,
      // Explicitly disable tool calling — Groq/Llama activates it by default
      tools: [],
      tool_choice: "none",
    };

    log.debug("api_call_start", {
      model: this.model,
      message_count: data.messages.length,
      temperature: this.temperature,
    });

    const startTime = Date.now();

    const response = await fetch(this.endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      log.error("api_call_failed", {
        status: response.status,
        body_preview: body.slice(0, 200),
        duration_ms: Date.now() - startTime,
      });
      throw new Error(`Groq API failed: ${response.status} — ${body}`);
    }

    const raw = (await response.json()) as GroqResponse;

    log.info("api_call_completed", {
      model: raw.model,
      prompt_tokens: raw.usage.prompt_tokens,
      completion_tokens: raw.usage.completion_tokens,
      total_tokens: raw.usage.total_tokens,
      finish_reason: raw.choices[0]?.finish_reason,
      duration_ms: Date.now() - startTime,
    });

    return {
      content: raw.choices[0].message.content,
      usage: {
        prompt_tokens: raw.usage.prompt_tokens,
        completion_tokens: raw.usage.completion_tokens,
        total_tokens: raw.usage.total_tokens,
      },
      cost: { input_cost: 0, output_cost: 0, total_cost: 0 },
      model: raw.model,
      provider: "groq",
    };
  }
}
