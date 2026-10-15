import { describe, it, expect } from "vitest";
import { ProviderConfigValidator } from "../../src/config/validator";
import type { AppConfig, ModelConfig, ProviderConfig } from "../../src/types/provider";

function makeModel(overrides: Partial<ModelConfig> = {}): ModelConfig {
  return {
    name: "model-a",
    maxTokens: 1024,
    supportsTools: true,
    ...overrides,
  };
}

function makeProvider(overrides: Partial<ProviderConfig> = {}): ProviderConfig {
  return {
    name: "openai",
    apiKeyEnv: "OPENAI_API_KEY",
    defaultModel: "model-a",
    models: [makeModel()],
    ...overrides,
  };
}

function makeConfig(overrides: Partial<AppConfig> = {}): AppConfig {
  return {
    providers: [makeProvider()],
    ...overrides,
  };
}

describe("ProviderConfigValidator", () => {
  it("accepts a fully valid config", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig();

    expect(validator.isValid(config)).toBe(true);
    expect(validator.validate(config)).toEqual([]);
  });

  it("reports an error at path providers when the list is empty", () => {
    const validator = new ProviderConfigValidator();

    const errors = validator.validate(makeConfig({ providers: [] }));

    expect(errors).toHaveLength(1);
    expect(errors[0].path).toBe("providers");
  });

  it("reports duplicate provider names", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig({
      providers: [makeProvider({ name: "dup" }), makeProvider({ name: "dup" })],
    });

    const errors = validator.validate(config);

    expect(errors.some((e) => e.message.includes("Duplicate provider name"))).toBe(true);
  });

  it("reports a provider with an empty models list at a .models path", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig({ providers: [makeProvider({ models: [] })] });

    const errors = validator.validate(config);

    expect(errors.some((e) => e.path.endsWith(".models"))).toBe(true);
  });

  it("reports a model with maxTokens equal to 0", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig({
      providers: [makeProvider({ models: [makeModel({ maxTokens: 0 })] })],
    });

    const errors = validator.validate(config);

    expect(errors.some((e) => e.message.includes("max_tokens must be a positive number"))).toBe(
      true,
    );
  });

  it("reports a model with a non-boolean supportsTools", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig({
      providers: [
        makeProvider({
          models: [makeModel({ supportsTools: "yes" as unknown as boolean })],
        }),
      ],
    });

    const errors = validator.validate(config);

    expect(errors.some((e) => e.message.includes("supports_tools must be a boolean"))).toBe(true);
  });

  it("reports a defaultModel that is not present in models", () => {
    const validator = new ProviderConfigValidator();
    const config = makeConfig({ providers: [makeProvider({ defaultModel: "ghost" })] });

    const errors = validator.validate(config);

    expect(errors.some((e) => e.message.includes("not found in models"))).toBe(true);
  });
});
