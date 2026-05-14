import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Loader2, Check, ChevronDown, ChevronRight } from "lucide-react";
import type { ToolStep } from "@/hooks/useChatStream";

interface ToolStepsProps {
  steps: ToolStep[];
}

function formatToolName(name: string): string {
  return name.replace(/_/g, " ");
}

export function ToolSteps({ steps }: ToolStepsProps) {
  const [expanded, setExpanded] = useState(false);

  // Auto-expand when there are running steps
  const hasRunning = steps.some((s) => s.status === "running");
  useEffect(() => {
    if (hasRunning) setExpanded(true);
  }, [hasRunning]);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className={cn(
          "inline-flex items-center gap-1 text-xs font-medium transition-colors",
          "text-muted-foreground hover:text-foreground",
        )}
      >
        {expanded ? (
          <ChevronDown className="size-3.5" />
        ) : (
          <ChevronRight className="size-3.5" />
        )}
        {expanded ? "Ocultar detalles" : "Mostrar detalles"}
      </button>

      {expanded && (
        <div className="mt-1.5 space-y-1">
          {steps.map((step, i) => (
            <div
              key={`${step.tool}-${i}`}
              className="flex items-center gap-2 text-xs font-mono"
            >
              {step.status === "running" ? (
                <Loader2 className="size-3.5 animate-spin shrink-0 text-primary" />
              ) : (
                <Check className="size-3.5 shrink-0 text-green-600 dark:text-green-400" />
              )}
              <span
                className={cn(
                  step.status === "running" && "text-primary",
                  step.status === "completed" && "text-muted-foreground",
                )}
              >
                {formatToolName(step.tool)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
