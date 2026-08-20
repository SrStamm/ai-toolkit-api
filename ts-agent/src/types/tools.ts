import { z } from "zod";
import type { Citation } from "./rag-api";

export type ToolResult =
  | { ok: true; output: string; metadata: ToolMetadata; complete?: boolean }
  | { ok: false; error: string; retryable: boolean };

export interface ToolMetadata {
  citations?: Citation[];
  taskId?: string;
  status?: string;
  source?: string;
  documents?: unknown[];
  count?: number;
  [key: string]: unknown;
}

export interface Tool<
  TInput extends Record<string, unknown> = Record<string, unknown>,
> {
  name: string;
  description: string;
  schema: z.ZodSchema<TInput>;
  dependencies: string[];
  execute: (input: TInput, deps: DependencyContainer) => Promise<ToolResult>;
}

export interface DependencyContainer {
  get<T>(key: string): T;
}

export interface CompleteToolResult extends ToolResult {
  complete: true;
}
