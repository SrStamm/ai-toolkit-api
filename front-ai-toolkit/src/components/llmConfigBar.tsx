import type { LLMProvider } from "@/types/llm";

interface LLMSelectorProps {
  provider: string;
  model: string;
  providers: LLMProvider[];
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
  isLoading?: boolean;
}

export function LLMSelector({
  provider,
  model,
  providers,
  onProviderChange,
  onModelChange,
  isLoading,
}: LLMSelectorProps) {
  const selectedProvider = providers.find((p) => p.name === provider);
  const models = selectedProvider?.models || [];

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onProviderChange(e.target.value);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onModelChange(e.target.value);
  };

  if (isLoading) {
    return <span className="text-xs text-muted-foreground">Cargando...</span>;
  }

  return (
    <div className="flex items-center gap-1">
      <select
        value={provider}
        onChange={handleProviderChange}
        className="bg-transparent text-sm font-medium border-0 focus:ring-0 cursor-pointer hover:bg-muted/50 rounded px-1.5 py-1"
      >
        {providers.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
          </option>
        ))}
      </select>

      <span className="text-muted-foreground/50">/</span>

      <select
        value={model}
        onChange={handleModelChange}
        className="bg-transparent text-sm border-0 focus:ring-0 cursor-pointer hover:bg-muted/50 rounded px-1.5 py-1"
      >
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
          </option>
        ))}
      </select>
    </div>
  );
}
