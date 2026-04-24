import type { AgentQuestion, AgentResponse } from "@/types/agent";
import Fetch from "@/utils/api";

export const agentAsk = async (body: AgentQuestion): Promise<AgentResponse> => {
  return await Fetch<AgentResponse>({
    path: "/agent/agent-loop",
    method: "POST",
    body: body,
  });
};
