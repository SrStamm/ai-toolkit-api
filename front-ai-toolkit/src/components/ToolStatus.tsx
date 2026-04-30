interface ToolStatusProps {
  status: string;
}

export function ToolStatus({ status }: ToolStatusProps) {
  return (
    <div className="text-xs text-muted-foreground mb-1 italic">
      {status}
    </div>
  );
}
