import type { AppConfig, ProviderConfig, ModelConfig } from "../types/provider";

export interface ValidationError {
  path: string;
  message: string;
}

export class ProviderConfigValidator {
  private errors: ValidationError[] = [];

  validate(config: AppConfig): ValidationError[] {
    this.errors = [];

    if (!config.providers || config.providers.length === 0) {
      this.errors.push({
        path: "providers",
        message: "At least one provider is required",
      });
      return this.errors;
    }

    this.validateUniqueProviderNames(config.providers);
    this.validateProviders(config.providers);

    return this.errors;
  }

  isValid(config: AppConfig): boolean {
    return this.validate(config).length === 0;
  }

  private validateUniqueProviderNames(providers: ProviderConfig[]): void {
    const names = providers.map((p) => p.name);
    const seen = new Set<string>();

    for (const name of names) {
      if (seen.has(name)) {
        this.errors.push({
          path: `providers.${name}`,
          message: `Duplicate provider name: '${name}'`,
        });
      }
      seen.add(name);
    }
  }

  private validateProviders(providers: ProviderConfig[]): void {
    for (const provider of providers) {
      this.validateProvider(provider);
    }
  }

  private validateProvider(provider: ProviderConfig): void {
    const prefix = `providers.${provider.name}`;

    if (!provider.name || provider.name.trim() === "") {
      this.errors.push({
        path: prefix,
        message: "Provider name is required",
      });
      return;
    }

    if (typeof provider.apiKeyEnv !== "string") {
      this.errors.push({
        path: `${prefix}.api_key_env`,
        message: "api_key_env must be a string",
      });
    }

    if (!provider.models || provider.models.length === 0) {
      this.errors.push({
        path: `${prefix}.models`,
        message: `Provider '${provider.name}' must have at least one model`,
      });
      return;
    }

    this.validateModels(provider);
    this.validateDefaultModel(provider);
  }

  private validateModels(provider: ProviderConfig): void {
    const prefix = `providers.${provider.name}`;
    const modelNames = provider.models.map((m) => m.name);
    const seen = new Set<string>();

    for (const model of provider.models) {
      if (seen.has(model.name)) {
        this.errors.push({
          path: `${prefix}.models.${model.name}`,
          message: `Duplicate model name: '${model.name}'`,
        });
      }
      seen.add(model.name);

      this.validateModel(model, prefix);
    }
  }

  private validateModel(model: ModelConfig, providerPrefix: string): void {
    const prefix = `${providerPrefix}.models.${model.name}`;

    if (!model.name || model.name.trim() === "") {
      this.errors.push({
        path: prefix,
        message: "Model name is required",
      });
    }

    if (typeof model.maxTokens !== "number" || model.maxTokens <= 0) {
      this.errors.push({
        path: `${prefix}.max_tokens`,
        message: `max_tokens must be a positive number, got: ${model.maxTokens}`,
      });
    }

    if (typeof model.supportsTools !== "boolean") {
      this.errors.push({
        path: `${prefix}.supports_tools`,
        message: `supports_tools must be a boolean, got: ${typeof model.supportsTools}`,
      });
    }
  }

  private validateDefaultModel(provider: ProviderConfig): void {
    if (!provider.defaultModel) return;

    const modelNames = provider.models.map((m) => m.name);
    const exists = modelNames.includes(provider.defaultModel);

    if (!exists) {
      this.errors.push({
        path: `providers.${provider.name}.default_model`,
        message: `default_model '${provider.defaultModel}' not found in models: [${modelNames.join(", ")}]`,
      });
    }
  }
}
