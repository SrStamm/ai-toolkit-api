import { useState, useEffect, useCallback } from "react";
import { getProviders } from "@/services/llmServices";
import type { LLMProvider } from "@/types/llm";
import { showToastError } from "@/components/toast";

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
