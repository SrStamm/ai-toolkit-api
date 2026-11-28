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
    signal?: AbortSignal,
  ) => Promise<ToolResult>;
}

export interface DependencyContainer {
  get<T>(key: string): T;
}

export type CompleteToolResult = Extract<ToolResult, { ok: true }> & {
  complete: true;
};

export interface ToolError {
  toolName: string;
  code: ToolErrorCode;
  message: string;
  retryable: boolean;
  timestamp: number;
}

export type ToolExecutionResult<T> =
  | { success: true; data: T }
  | { success: false; error: ToolError };

export const ToolErrorCodes = {
  TIMEOUT: "TIMEOUT",
  NETWORK_ERROR: "NETWORK_ERROR",
  RATE_LIMITED: "RATE_LIMITED",
  HTTP_5XX: "http_error",
  BAD_REQUEST: "bad_request",
  NOT_FOUND: "not_found",
  TOOL_NOT_FOUND: "TOOL_NOT_FOUND",
  INVALID_RESPONSE: "INVALID_RESPONSE",
  CANCELLED: "CANCELLED",
  HTTP_4XX: "HTTP_4XX",
  UNKNOWN: "UNKNOWN",
} as const;

export type ToolErrorCode =
  (typeof ToolErrorCodes)[keyof typeof ToolErrorCodes];
