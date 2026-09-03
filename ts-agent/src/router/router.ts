import { LLMInterface } from "../lib/llm/client";
import "../tools";
import { listTools } from "../tools/registry";
import { ActionType, Decision, ToolContext } from "../types/agent";
import { Message } from "../types/llm";
import { applyGuardrails } from "./guardrails";
import { buildRoutingPrompt } from "./prompts";
import { z } from "zod";

const decisionSchema = z.discriminatedUnion("action", [
  z.object({
    action: z.literal("call_tool"),
    tool_name: z.string(),
    args: z.record(z.string(), z.unknown()).default({}),
  }),
  z.object({
    action: z.literal("ask_user"),
    message: z.string(),
  }),
  z.object({
    action: z.literal("final_answer"),
  }),
]);

export class Router {
  private llm: LLMInterface;

  constructor(llm: LLMInterface) {
    this.llm = llm;
  }

  private buildToolList(): string {
    const toolList = listTools()
      .map((t) => `- ${t.name}: ${t.description}`)
      .join("\n");

    return toolList;
  }

  async getDecision(
    query: string,
    ctx: ToolContext,
    history?: Message[],
  ): Promise<Decision> {
    const toolList = this.buildToolList();

    const systemPrompt = buildRoutingPrompt(toolList, ctx);

    const messages: Message[] = history
      ? [...history, { role: "user", content: query }]
      : [{ role: "user", content: query }];

    const response = await this.llm.chat(messages, systemPrompt);

    try {
      const decision = decisionSchema.parse(JSON.parse(response.content));
      const finalDecision = applyGuardrails(decision, ctx);

      return finalDecision;
    } catch (error) {
      return { action: ActionType.FINAL_ANSWER };
    }
  }
}
