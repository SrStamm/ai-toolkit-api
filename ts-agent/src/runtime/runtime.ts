import { LLMInterface } from "../lib/llm/client";
import { buildFinalAnswerPrompt } from "../router/prompts";
import { Router } from "../router/router";
import { getTool } from "../tools/registry";
import {
  ActionType,
  AgentInput,
  AgentState,
  Decision,
  RuntimeConfig,
  RuntimeState,
  StepTrace,
  StreamEvent,
} from "../types/agent";
import { CostBreakdown, Message } from "../types/llm";
import { ToolResult } from "../types/tools";
import { redisClient, SessionMemory } from "../lib/session-memory";

const DEFAULT_CONFIG: RuntimeConfig = {
  maxSteps: 5,
  stepTimeoutMs: 30_000,
  totalTimeoutMs: 120_000,
  maxRetries: 2,
  retryBackoffMs: 500,
};

class Runtime {
  private llm: LLMInterface;
  private router: Router;
  private config: RuntimeConfig;
  private sessionMemory: SessionMemory;

  private state: AgentState | null = null;
  private traces: StepTrace[] = [];
  private currentStep = 0;
  private totalCost: CostBreakdown = {
    input_cost: 0,
    output_cost: 0,
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
    this.state.history.push(userMessage);
  }

  async *runStream(input: AgentInput) {
    this.state = await this.initState(input);

    await this.updateMemory(input.query, "user", input.session_id);

    yield this.emitEvent("state_changed", {
      type: "state_changed",
      state: RuntimeState.THINKING,
    });

    for (
      this.currentStep = 0;
      this.currentStep < this.config.maxSteps;
      this.currentStep++
    ) {
      const decision = await this.router.getDecision(
        this.state.query,
        this.state.toolContext,
        this.state.history,
      );

      yield this.emitEvent("agent_decision", {
        type: "agent_decision",
        decision: decision,
      });

      switch (decision.action) {
        case ActionType.ASK_USER: {
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
          return;
        }

        case ActionType.CALL_TOOL: {
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

            return;
          }
          break;
        }

        case ActionType.FINAL_ANSWER: {
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

          return;
        }
      }
    }
  }

  async main(input: AgentInput) {
    this.state = await this.initState(input);
    this.traces = [];
    this.currentStep = 0;

    await this.sessionMemory.add(input.session_id, {
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
        const result = await Promise.race([
          tool.execute(decision.args, /* deps */ null as any),
          this.timeout(this.config.stepTimeoutMs),
        ]);

        // Registrar trace
        this.traces.push({
          step: this.currentStep,
          action: ActionType.CALL_TOOL,
          toolName: decision.tool_name,
          args: decision.args,
          resultPreview: result.ok ? result.output.slice(0, 200) : result.error,
          durationMs: Date.now() - startMs,
          timestamp: Date.now(),
        });

        return result as ToolResult;
      } catch (err) {
        lastError = {
          ok: false,
          error: err instanceof Error ? err.message : String(err),
          retryable: true,
        };

        if (attempt < this.config.maxRetries) {
          await this.sleep(this.config.retryBackoffMs * (attempt + 1));
        }
      }
    }

    return lastError!;
  }

  private async initState(input: AgentInput): Promise<AgentState> {
    const history = await this.sessionMemory.getHistory(input.session_id);

    return {
      query: input.query,
      session_id: input.session_id,
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

    const systemPrompt = buildFinalAnswerPrompt(context);

    const messages: Message[] = [
      ...(this.state!.history ?? []),
      { role: "user", content: this.state!.query },
    ];

    const response = await this.llm.chat(messages, systemPrompt);
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
