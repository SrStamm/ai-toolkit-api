import type { AgentQuestion, AgentResponse } from "@/types/agent";
import Fetch from "@/utils/api";

interface AgentAskOptions {
  provider?: string;
  model?: string;
}

export const agentAsk = async (body: AgentQuestion, options: AgentAskOptions = {}): Promise<AgentResponse> => {
  const headers: Record<string, string> = {};
  
  if (options.provider) {
    headers["x-llm-provider"] = options.provider;
  }
  if (options.model) {
    headers["x-llm-model"] = options.model;
  }
  
  return await Fetch<AgentResponse>({
    path: "/agent/agent-loop",
    method: "POST",
    body: body,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
  });
};