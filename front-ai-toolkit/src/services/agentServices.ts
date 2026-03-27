import type { AgentQuestion } from "@/types/agent";
import Fetch from "@/utils/api";

export const agentAsk = async (body: AgentQuestion) => {
  return await Fetch({
    path: "/agent/ask-custom",
    method: "POST",
    body: body,
  });
};
