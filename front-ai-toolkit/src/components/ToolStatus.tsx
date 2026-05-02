interface ToolStatusProps {
  status: string;
  taskId?: string; // Celery task ID for background jobs
}

export function ToolStatus({ status, taskId }: ToolStatusProps) {
  return (
    <div className="text-xs text-muted-foreground mb-1 italic space-y-1">
      <div>{status}</div>
      {taskId && (
        <div className="font-mono text-[10px] bg-muted/50 p-1 rounded">
          Task ID: <span className="select-all">{taskId}</span>
        </div>
      )}
    </div>
  );
}
