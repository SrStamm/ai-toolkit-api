interface CitationsListProps {
  sources: string[];
}

export function CitationsList({ sources }: CitationsListProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 text-xs text-muted-foreground">
      <p className="font-semibold mb-1">Sources:</p>
      <ul className="list-disc list-outside pl-4 space-y-0.5">
        {sources.map((source, idx) => (
          <li key={idx} className="italic">
            {source}
          </li>
        ))}
      </ul>
    </div>
  );
}
