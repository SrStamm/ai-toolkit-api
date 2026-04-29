import { useState, useEffect, useCallback } from "react";
import { getProviders } from "@/services/llmServices";
import type { LLMProvider } from "@/types/llm";
import { showToastError } from "./toast";
import { cn } from "@/lib/utils";

interface UseLLMConfigReturn {
  provider: string;
  model: string;
  providers: LLMProvider[];
  isLoaded: boolean;
  useStream: boolean;
  setProvider: (provider: string) => void;
  setModel: (model: string) => void;
  setUseStream: (useStream: boolean) => void;
}

export function useLLMConfig(): UseLLMConfigReturn {
  const [provider, setProviderState] = useState("");
  const [model, setModelState] = useState("");
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [useStream, setUseStreamState] = useState(false);

  const setProvider = useCallback(
    (newProvider: string) => {
      const providerConfig = providers.find((p) => p.name === newProvider);
      if (providerConfig) {
        setProviderState(newProvider);
        // Auto-set model to default when provider changes
        setModelState(
          providerConfig.default_model || providerConfig.models[0]?.name || "",
        );
      }
    },
    [providers],
  );

  const setModel = useCallback((newModel: string) => {
    setModelState(newModel);
  }, []);

  useEffect(() => {
    const loadProviders = async () => {
      try {
        const data = await getProviders();
        setProviders(data);

        if (data.length > 0) {
          const defaultProvider = data[0];
          setProviderState(defaultProvider.name);
          setModelState(
            defaultProvider.default_model ||
              defaultProvider.models[0]?.name ||
              "",
          );
        }
        setIsLoaded(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Error al cargar providers";
        showToastError(errorMessage);
        setIsLoaded(true);
      }
    };

    loadProviders();
  }, []);

  return {
    provider,
    model,
    providers,
    isLoaded,
    useStream,
    setProvider,
    setModel,
    setUseStream: setUseStreamState,
  };
}

interface LLMSelectorProps {
  provider: string;
  model: string;
  providers: LLMProvider[];
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
  isLoading?: boolean;
  useStream: boolean;
  onStreamChange: (useStream: boolean) => void;
}

export function LLMSelector({
  provider,
  model,
  providers,
  onProviderChange,
  onModelChange,
  isLoading,
  useStream,
  onStreamChange,
}: LLMSelectorProps) {
  const selectedProvider = providers.find((p) => p.name === provider);
  const models = selectedProvider?.models || [];

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onProviderChange(e.target.value);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onModelChange(e.target.value);
  };

  const handleStreamToggle = () => {
    onStreamChange(!useStream);
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

      <span className="text-muted-foreground/50">/</span>

      <button
        onClick={handleStreamToggle}
        className={cn(
          "text-xs px-2 py-1 rounded border transition-colors",
          useStream
            ? "bg-primary/10 text-primary border-primary/20"
            : "bg-muted/50 text-muted-foreground border-transparent hover:bg-muted"
        )}
        title={useStream ? "Streaming enabled" : "Streaming disabled"}
      >
        {useStream ? "Stream ON" : "Stream OFF"}
      </button>
    </div>
  );
}

