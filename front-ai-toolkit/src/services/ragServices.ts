import type { Ingestrequest, QueryRequest } from "@/types/rag";
import Fetch from "@/utils/api";

export const ingestURLFetch = async (body: Ingestrequest) => {
  return await Fetch({ path: "/rag/ingest", method: "POST", body: body });
};

export const askFetch = async (body: QueryRequest) => {
  return await Fetch({ path: "/rag/ask", method: "POST", body: body });
};
