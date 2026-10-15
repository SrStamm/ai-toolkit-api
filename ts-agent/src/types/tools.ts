import { z } from "zod";
import type { Citation, SourceMetadata } from "./rag-api";

export type ToolResult =
  | { ok: true; output: string; metadata: ToolMetadata; complete?: boolean }
  | { ok: false; error: string; retryable: boolean };

export interface ToolMetadata {
  citations?: Citation[];
  taskId?: string;
  status?: string;
  source?: string;
  documents?: SourceMetadata[];
  count?: number;
}

export interface Tool<TSchema extends z.ZodType = z.ZodType> {
  name: string;
  description: string;
  schema: TSchema;
  dependencies: string[];
  execute: (
    input: z.output<TSchema>,
    deps: DependencyContainer,
  ) => Promise<ToolResult>;
}

export interface DependencyContainer {
  get<T>(key: string): T;
}

export type CompleteToolResult = Extract<ToolResult, { ok: true }> & {
  complete: true;
};
