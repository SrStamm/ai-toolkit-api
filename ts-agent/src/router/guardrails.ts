import { ActionType, Decision, ToolContext } from "../types/agent";

export function applyGuardrails(
  decision: Decision,
  ctx: ToolContext,
): Decision {
  if (decision.action == ActionType.CALL_TOOL) {
    // Evita llamar a retrieve tool
    if (decision.tool_name == "retrieve_context" && ctx.hasContext) {
      return { action: ActionType.FINAL_ANSWER };
    }

    // Evita llamar dos veces a la misma tool
    if (decision.tool_name == ctx.lastTool) {
      return { action: ActionType.FINAL_ANSWER };
    }

    return decision;
  }
}
