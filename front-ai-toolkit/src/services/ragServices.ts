import type { Ingestrequest, QueryRequest } from "@/types/rag";
import Fetch from "@/utils/api";

export const ingestURLFetch = async (body: Ingestrequest) => {
  return await Fetch({ path: "/rag/ingest", method: "POST", body: body });
};

export const askFetch = async (body: QueryRequest) => {
  return await Fetch({ path: "/rag/ask", method: "POST", body: body });
};

export const askStreamFetch = async (body: QueryRequest): Promise<Response> => {
  const response = await fetch("http://localhost:8000/rag/ask-stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response; // Devolver el Response raw para acceder al stream
};
