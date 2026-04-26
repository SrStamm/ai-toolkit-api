import { useState, useEffect, useCallback } from "react";
import { getProviders } from "@/services/llmServices";
import type { LLMProvider, LLMModel } from "@/types/llm";
import { showToastError } from "./toast";

interface UseLLMConfigReturn {
  provider: string;
  model: string;
  providers: LLMProvider[];
  isLoaded: boolean;
  setProvider: (provider: string) => void;
  setModel: (model: string) => void;
}

export function useLLMConfig(): UseLLMConfigReturn {
  const [provider, setProviderState] = useState("");
  const [model, setModelState] = useState("");
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  const setProvider = useCallback((newProvider: string) => {
    const providerConfig = providers.find(p => p.name === newProvider);
    if (providerConfig) {
      setProviderState(newProvider);
      // Auto-set model to default when provider changes
      setModelState(providerConfig.default_model || providerConfig.models[0]?.name || "");
    }
  }, [providers]);

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
          setModelState(defaultProvider.default_model || defaultProvider.models[0]?.name || "");
        }
        setIsLoaded(true);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Error al cargar providers";
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
    setProvider,
    setModel,
  };
}

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
  isLoading 
}: LLMSelectorProps) {
  const selectedProvider = providers.find(p => p.name === provider);
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