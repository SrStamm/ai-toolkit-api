import { ActionType, Decision, ToolContext } from "../types/agent";
import { logger } from "../lib/logger";

const log = logger.child("guardrails");

export function applyGuardrails(
  decision: Decision,
  ctx: ToolContext,
): Decision {
  if (decision.action == ActionType.CALL_TOOL) {
    // Evita llamar a retrieve tool
    if (decision.tool_name == "retrieve_context" && ctx.hasContext) {
      log.warn("guardrail_block_duplicate_retrieve", {
        tool_name: decision.tool_name,
        has_context: ctx.hasContext,
      });
      return { action: ActionType.FINAL_ANSWER };
    }

    // Evita llamar dos veces a la misma tool
    if (decision.tool_name == ctx.lastTool) {
      log.warn("guardrail_block_repeat_tool", {
        tool_name: decision.tool_name,
        last_tool: ctx.lastTool,
      });
      return { action: ActionType.FINAL_ANSWER };
    }
  }

  return decision;
}
