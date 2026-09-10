import { SessionMemory, redisClient } from "../lib/session-memory";
import { logger } from "../lib/logger";
import { LLMInterface } from "../lib/llm/client";
import {
  ActionType,
  AgentInput,
  AgentState,
  Decision,
  RuntimeConfig,
  RuntimeState,
  StepTrace,
  StreamEvent,
  ToolContext,
} from "../types/agent";
import { Message } from "../types/llm";
import { ToolResult } from "../types/tools";
import { Router } from "../router/router";
import { getTool } from "../tools/registry";
import { buildFinalAnswerPrompt } from "../router/prompts";

const log = logger.child("runtime");

const DEFAULT_CONFIG: RuntimeConfig = {
  maxSteps: 5,
  stepTimeoutMs: 30_000,
  totalTimeoutMs: 120_000,
  maxRetries: 2,
  retryBackoffMs: 1_000,
};

export class Runtime {
  private llm: LLMInterface;
  private router: Router;
  private sessionMemory: SessionMemory;
  private config: RuntimeConfig;
  private state!: AgentState;
  private traces: StepTrace[] = [];
  private currentStep = 0;

  private stats = {
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_cost: 0,
  };

  constructor(
    llm: LLMInterface,
    sessionMemory: SessionMemory,
    config?: Partial<RuntimeConfig>,
  ) {
    this.llm = llm;
    this.router = new Router(llm);
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.sessionMemory = sessionMemory;
  }

  private emitEvent<T extends StreamEvent["type"]>(
    event: T,
    data: Extract<StreamEvent, { type: T }>,
  ): string {
    return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  }

  extractAnswer(answer: string): string {
    if (!answer) return "";

    let content = answer.trim();

    content = content.replace(/^```(?:json|text)?\n?/, "").replace(/```$/, "");

    if (content.startsWith("{") && content.endsWith("}")) {
      try {
        const parsed = JSON.parse(content);
        if (typeof parsed === "object" && parsed !== null) {
          // Common field names that might contain the answer
          const possibleKeys = [
            "answer",
            "response",
            "text",
            "content",
            "message",
          ];
          for (const key of possibleKeys) {
            if (key in parsed && typeof parsed[key] === "string") {
              content = parsed[key];
              break;
            }
          }
          // If single key, use its value
          const keys = Object.keys(parsed);
          if (keys.length === 1 && typeof parsed[keys[0]] === "string") {
            content = parsed[keys[0]];
          }
        }
      } catch {
        // Not valid JSON, continue with original
      }
    }

    return content.trim();
  }

  async updateMemory(
    query: string,
    role: "user" | "assistant",
    session_id: string,
  ) {
    const userMessage: Message = {
      role: role,
      content: query,
    };

    await this.sessionMemory.add(session_id, userMessage);
    this.state?.history?.push(userMessage);

    log.debug("memory_updated", { session_id, role, content_len: query.length });
  }

  async *runStream(input: AgentInput) {
    const startTime = Date.now();

    // Generate session_id if not provided
    const sessionId = input.session_id || crypto.randomUUID();
    const resolvedInput = { ...input, session_id: sessionId };

    log.info("stream_started", {
      session_id: sessionId,
      query_preview: input.query.slice(0, 100),
      has_file: !!input.file_uuid,
    });

    this.state = await this.initState(resolvedInput);

    await this.updateMemory(input.query, "user", sessionId);

    yield this.emitEvent("state_changed", {
      type: "state_changed",
      state: RuntimeState.THINKING,
    });

    for (
      this.currentStep = 0;
      this.currentStep < this.config.maxSteps;
      this.currentStep++
    ) {
      log.debug("step_begin", {
        step: this.currentStep,
        session_id: sessionId,
      });

      const decision = await this.router.getDecision(
        this.state.query,
        this.state.toolContext,
        this.state.history,
      );

      log.info("agent_decision", {
        step: this.currentStep,
        action: decision.action,
        tool_name: "tool_name" in decision ? decision.tool_name : undefined,
        session_id: sessionId,
      });

      yield this.emitEvent("agent_decision", {
        type: "agent_decision",
        decision: decision,
      });

      switch (decision.action) {
        case ActionType.ASK_USER: {
          log.info("action_ask_user", {
            step: this.currentStep,
            message_preview: decision.message.slice(0, 100),
          });
          yield this.emitEvent("state_changed", {
            type: "state_changed",
            state: RuntimeState.WAITING_USER,
          });
          yield this.emitEvent("llm_token", {
            type: "llm_token",
            token: decision.message,
          });
          yield this.emitEvent("done", {
            type: "done",
            sessionId: this.state.session_id,
            content: decision.message,
            metadata: {
              citations: this.state.toolContext.citations,
            },
          });
          log.info("stream_completed", {
            reason: "ask_user",
            duration_ms: Date.now() - startTime,
            steps: this.currentStep + 1,
          });
          return;
        }

        case ActionType.CALL_TOOL: {
          log.info("action_call_tool", {
            step: this.currentStep,
            tool_name: decision.tool_name,
            args: decision.args,
          });
          yield this.emitEvent("state_changed", {
            type: "state_changed",
            state: RuntimeState.EXECUTING_TOOL,
            tool: decision.tool_name,
          });

          const result = await this.executeToolWithRetry({
            ...decision,
            args: { ...decision.args, query: this.state.query },
          });

          this.updateContext(decision.tool_name, result);

          yield this.emitEvent("tool_done", {
            type: "tool_done",
            tool: decision.tool_name,
            status: result.ok ? "success" : "error",
          });

          if (result.ok && result.complete) {
            log.info("tool_complete_early_return", {
              tool_name: decision.tool_name,
              output_len: result.output.length,
            });
            yield this.emitEvent("llm_token", {
              type: "llm_token",
              token: result.output,
            });
            yield this.emitEvent("done", {
              type: "done",
              sessionId: this.state.session_id,
              content: result.output,
              metadata: result.metadata,
            });
            yield this.emitEvent("state_changed", {
              type: "state_changed",
              state: RuntimeState.COMPLETED,
            });

            log.info("stream_completed", {
              reason: "tool_complete",
              tool_name: decision.tool_name,
              duration_ms: Date.now() - startTime,
              steps: this.currentStep + 1,
            });
            return;
          }
          break;
        }

        case ActionType.FINAL_ANSWER: {
          log.info("action_final_answer", { step: this.currentStep });
          yield this.emitEvent("state_changed", {
            type: "state_changed",
            state: RuntimeState.GENERATING,
          });

          const raw = await this.generateAnswer();
          const answer = this.extractAnswer(raw);

          yield this.emitEvent("llm_token", {
            type: "llm_token",
            token: answer,
          });

          yield this.emitEvent("done", {
            type: "done",
            sessionId: this.state.session_id,
            content: answer,
            metadata: {
              citations: this.state.toolContext.citations,
            },
          });

          yield this.emitEvent("state_changed", {
            type: "state_changed",
            state: RuntimeState.COMPLETED,
          });

          await this.updateMemory(answer, "assistant", this.state.session_id);

          log.info("stream_completed", {
            reason: "final_answer",
            answer_len: answer.length,
            duration_ms: Date.now() - startTime,
            steps: this.currentStep + 1,
          });
          return;
        }
      }
    }

    log.warn("max_steps_reached", {
      max_steps: this.config.maxSteps,
      session_id: sessionId,
      duration_ms: Date.now() - startTime,
    });
  }

  async main(input: AgentInput) {
    const sessionId = input.session_id || crypto.randomUUID();
    const resolvedInput = { ...input, session_id: sessionId };

    this.state = await this.initState(resolvedInput);
    this.traces = [];
    this.currentStep = 0;

    await this.sessionMemory.add(sessionId, {
      role: "user",
      content: input.query,
    });

    return this.execution_loop();
  }

  async execution_loop() {
    for (
      this.currentStep = 0;
      this.currentStep < this.config.maxSteps;
      this.currentStep++
    ) {
      // Obtener una decision del router
      const decision = await this.router.getDecision(
        this.state!.query,
        this.state!.toolContext,
        this.state!.history,
      );

      log.info("loop_decision", {
        step: this.currentStep,
        action: decision.action,
        tool_name: "tool_name" in decision ? decision.tool_name : undefined,
      });

      switch (decision.action) {
        case ActionType.ASK_USER: {
          return { content: decision.message, metadata: {} };
        }

        case ActionType.FINAL_ANSWER: {
          const answer = await this.generateAnswer();

          await this.sessionMemory.add(this.state!.session_id, {
            role: "assistant",
            content: answer,
          });

          return { content: answer, metadata: {} };
        }

        case ActionType.CALL_TOOL: {
          const toolArgs = {
            ...decision.args,
            query: this.state!.query,
          };

          const result = await this.executeToolWithRetry({
            ...decision,
            args: toolArgs,
          });

          // Actualizar state
          this.updateContext(decision.tool_name, result);

          if (result.ok && result.complete) {
            this.state!.status = RuntimeState.COMPLETED;

            await this.sessionMemory.add(this.state!.session_id, {
              role: "assistant",
              content: result.output,
            });

            return;
          }

          break;
        }
      }
    }
  }

  // function to execute a tool
  private async executeToolWithRetry(
    decision: Extract<Decision, { action: ActionType.CALL_TOOL }>,
  ): Promise<ToolResult> {
    const tool = getTool(decision.tool_name);

    if (!tool) {
      log.error("tool_not_found", {
        tool_name: decision.tool_name,
        available_tools: "retrieve_context,list_documents,delete_document,get_document_metadata",
      });
      return {
        ok: false,
        error: `Tool '${decision.tool_name}' not found`,
        retryable: false,
      };
    }

    let lastError: ToolResult | null = null;

    for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
      const startMs = Date.now();

      try {
        log.debug("tool_execution_start", {
          tool_name: decision.tool_name,
          attempt,
          max_retries: this.config.maxRetries,
          args: decision.args,
        });

        const result = await Promise.race([
          tool.execute(decision.args, /* deps */ null as any),
          this.timeout(this.config.stepTimeoutMs),
        ]);

        const durationMs = Date.now() - startMs;
        const toolResult = result as ToolResult;

        log.info("tool_execution_completed", {
          tool_name: decision.tool_name,
          attempt,
          ok: toolResult.ok,
          duration_ms: durationMs,
          output_len: toolResult.ok ? toolResult.output.length : undefined,
          error: toolResult.ok ? undefined : toolResult.error,
        });

        // Registrar trace
        this.traces.push({
          step: this.currentStep,
          action: ActionType.CALL_TOOL,
          toolName: decision.tool_name,
          args: decision.args,
          resultPreview: toolResult.ok ? toolResult.output.slice(0, 200) : toolResult.error,
          durationMs,
          timestamp: Date.now(),
        });

        return toolResult;
      } catch (err) {
        const durationMs = Date.now() - startMs;
        const errorMsg = err instanceof Error ? err.message : String(err);

        log.error("tool_execution_error", {
          tool_name: decision.tool_name,
          attempt,
          duration_ms: durationMs,
          error: errorMsg,
          is_timeout: errorMsg === "Step timeout",
        });

        lastError = {
          ok: false,
          error: errorMsg,
          retryable: true,
        };

        if (attempt < this.config.maxRetries) {
          const backoff = this.config.retryBackoffMs * (attempt + 1);
          log.debug("tool_retry_backoff", {
            tool_name: decision.tool_name,
            attempt,
            next_attempt: attempt + 1,
            backoff_ms: backoff,
          });
          await this.sleep(backoff);
        }
      }
    }

    log.error("tool_all_retries_exhausted", {
      tool_name: decision.tool_name,
      total_attempts: this.config.maxRetries + 1,
      last_error: lastError?.error,
    });

    return lastError!;
  }

  private async initState(input: AgentInput): Promise<AgentState> {
    const sessionId = input.session_id || crypto.randomUUID();
    const history = await this.sessionMemory.getHistory(sessionId);

    log.debug("state_initialized", {
      session_id: sessionId,
      history_size: history.length,
      has_domain: !!input.domain,
    });

    return {
      query: input.query,
      session_id: sessionId,
      domain: input.domain,
      file_uuid: input.file_uuid,
      filename: input.filename,
      history: history.length > 0 ? history : (input.history ?? []),
      status: RuntimeState.THINKING,
      toolContext: {
        citations: [],
        hasContext: false,
        toolExecutionCount: 0,
      },
    };
  }

  private updateContext(toolName: string, result: ToolResult): void {
    const ctx = this.state!.toolContext;
    ctx.lastTool = toolName;
    ctx.toolExecutionCount++;

    if (result.ok) {
      ctx.lastToolResult = result.output;
      ctx.hasContext = true;
      if (result.metadata.citations) {
        ctx.citations.push(...result.metadata.citations);
      }
    }

    log.debug("context_updated", {
      tool_name: toolName,
      ok: result.ok,
      has_context: ctx.hasContext,
      execution_count: ctx.toolExecutionCount,
      citation_count: ctx.citations.length,
    });
  }

  private timeout(ms: number): Promise<never> {
    return new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Step timeout")), ms),
    );
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private async generateAnswer(): Promise<string> {
    const context = this.state?.toolContext.hasContext
      ? this.state.toolContext.lastToolResult
      : undefined;

    log.debug("generate_answer_start", {
      has_context: !!context,
      context_len: context?.length,
      history_size: this.state!.history?.length,
    });

    const systemPrompt = buildFinalAnswerPrompt(context);

    const messages: Message[] = [
      ...(this.state!.history ?? []),
      { role: "user", content: this.state!.query },
    ];

    const response = await this.llm.chat(messages, systemPrompt);

    log.debug("generate_answer_completed", {
      response_len: response.content.length,
    });

    return response.content;
  }
}

export function createRuntime(
  llm: LLMInterface,
  config?: Partial<RuntimeConfig>,
) {
  const sessionMemory = new SessionMemory(redisClient);
  return new Runtime(llm, sessionMemory, config);
}
