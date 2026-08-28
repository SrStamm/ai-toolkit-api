import type { Citation } from "./rag-api";
import type { CostBreakdown, Message } from "./llm";
import { ToolMetadata } from "./tools";

export enum ActionType {
  CALL_TOOL = "call_tool",
  ASK_USER = "ask_user",
  FINAL_ANSWER = "final_answer",
}

export enum RuntimeState {
  THINKING = "thinking",
  EXECUTING_TOOL = "executing_tool",
  WAITING_USER = "waiting_user",
  COMPLETED = "completed",
  FAILED = "failed",
  GENERATING = "generating",
}

export interface AgentInput {
  query: string;
  session_id: string;
  top_k?: number;
  domain?: string; // Dominio opcional para filtrar búsquedas
  history?: Message[];
  file_uuid?: string;
  filename?: string;
}

export interface ToolContext {
  hasContext: boolean;
  lastTool?: string;
  lastToolResult?: string;
  lastToolMetadata?: Record<string, unknown>;
  toolExecutionCount: number;
  citations: Citation[];
}

export interface AgentState {
  query: string;
  session_id: string;
  top_k?: number;
  domain?: string;
  history?: Message[];
  file_uuid?: string;
  filename?: string;
  status: RuntimeState;
  toolContext: ToolContext;
}

export type Decision =
  | {
      action: ActionType.CALL_TOOL;
      tool_name: string;
      args: Record<string, unknown>;
    }
  | { action: ActionType.ASK_USER; message: string }
  | { action: ActionType.FINAL_ANSWER };

export type AgentEvent =
  | { type: "llm_token"; token: string }
  | { type: "tool_done"; tool: string; status: "success" | "error" }
  | { type: "agent_decision"; decision: Decision }
  | { type: "state_changed"; state: RuntimeState; tool?: string }
  | { type: "done"; content: string; metadata: ToolMetadata }
  | { type: "error"; error: string };

export interface StepTrace {
  step: number;
  action: ActionType;
  toolName?: string;
  args: Record<string, unknown>;
  resultPreview?: string;
  durationMs: number;
  timestamp: number;
  error?: string;
}

export interface RuntimeConfig {
  maxSteps: number;
  stepTimeoutMs: number;
  totalTimeoutMs: number;
  maxRetries: number;
  retryBackoffMs: number;
}

export interface LoopResult {
  status: RuntimeState;
  steps: StepTrace[];
  finalAnswer?: string;
  totalDurationMs: number;
  totalTokens: number;
  totalCost: CostBreakdown;
  error?: string;
}

export type StreamEvent =
  | { type: "llm_token"; token: string }
  | { type: "tool_done"; tool: string; status: "success" | "error" }
  | { type: "agent_decision"; decision: Decision }
  | { type: "state_changed"; state: RuntimeState; tool?: string }
  | { type: "done"; content: string; metadata: ToolMetadata }
  | { type: "error"; error: string };
