import { LLMInterface } from "../lib/llm/client";
import { getLlmProvider } from "../lib/llm/factory";
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
} from "../types/agent";
import { CostBreakdown } from "../types/llm";
import { ToolResult } from "../types/tools";

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

  private state: AgentState | null = null;
  private traces: StepTrace[] = [];
  private currentStep = 0;
  private totalCost: CostBreakdown = {
    input_cost: 0,
    output_cost: 0,
    total_cost: 0,
  };

  constructor(llm: LLMInterface, config?: Partial<RuntimeConfig>) {
    this.llm = llm;
    this.router = new Router(llm);
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  async main(input: AgentInput) {
    this.state = this.initState(input);
    this.traces = [];
    this.currentStep = 0;

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

      console.log("decision: ", decision);

      switch (decision.action) {
        case ActionType.ASK_USER: {
          return { content: decision.message, metadata: {} };
        }

        case ActionType.FINAL_ANSWER: {
          const answer = await this.generateAnswer();
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
            console.log(
              `type: done, content: ${result.output}, metadata: ${result.metadata}`,
            );
            this.state!.status = RuntimeState.COMPLETED;
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

    console.log(tool);

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

        console.log("toolResult: ", result);

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

  private initState(input: AgentInput): AgentState {
    return {
      query: input.query,
      session_id: input.session_id,
      domain: input.domain,
      file_uuid: input.file_uuid,
      filename: input.filename,
      history: input.history ?? [],
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

    console.log("Tool Context: ", this.state?.toolContext);
    console.log("Context: ", context);

    const systemPrompt = buildFinalAnswerPrompt(context);

    console.log("systemPrompt: ", systemPrompt);

    const response = await this.llm.chat(
      [{ role: "user", content: this.state!.query }],
      systemPrompt,
    );
    return response.content;
  }
}
