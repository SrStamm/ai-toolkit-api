import type { LLMConfigResponse, LLMProvider } from "@/types/llm";
import Fetch from "@/utils/api";

export const getProviders = async (): Promise<LLMProvider[]> => {
  const response = await Fetch<LLMConfigResponse>({
    path: "/agent/providers",
    method: "GET",
  });
  return response.providers;
};