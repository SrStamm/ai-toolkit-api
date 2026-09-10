import { LLMInterface } from "../lib/llm/client";
import { logger } from "../lib/logger";
import "../tools";
import { listTools } from "../tools/registry";
import { ActionType, Decision, ToolContext } from "../types/agent";
import { Message } from "../types/llm";
import { applyGuardrails } from "./guardrails";
import { buildRoutingPrompt } from "./prompts";
import { z } from "zod";

const log = logger.child("router");

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

    log.debug("llm_call_start", {
      query_preview: query.slice(0, 80),
      has_context: ctx.hasContext,
      has_history: !!history?.length,
      tool_count: listTools().length,
    });

    const response = await this.llm.chat(messages, systemPrompt);

    log.debug("llm_call_completed", {
      response_len: response.content.length,
    });

    try {
      const parsed = JSON.parse(response.content);
      const decision = decisionSchema.parse(parsed);
      const finalDecision = applyGuardrails(decision as Decision, ctx);

      log.info("decision_parsed", {
        raw_action: decision.action,
        final_action: finalDecision.action,
        tool_name: "tool_name" in finalDecision ? finalDecision.tool_name : undefined,
        guardrails_applied: decision.action !== finalDecision.action,
      });

      return finalDecision;
    } catch (error) {
      log.warn("decision_parse_failed", {
        raw_response: response.content.slice(0, 200),
        error: error instanceof Error ? error.message : String(error),
      });
      return { action: ActionType.FINAL_ANSWER };
    }
  }
}
