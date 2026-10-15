// llm client interface and factory
import { LLMResponse, Message } from "../../types/llm";

export interface LLMInterface {
  chat(messages: Message[], systemPrompt: string): Promise<LLMResponse>;
}
