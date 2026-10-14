import { describe, it, expect, afterAll } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { loadProvidersConfig } from "../../src/config/loader";

const tempDirs: string[] = [];

function writeTempYaml(content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "ts-agent-config-"));
  tempDirs.push(dir);
  const file = join(dir, "providers.yaml");
  writeFileSync(file, content, "utf-8");
  return file;
}

afterAll(() => {
  for (const dir of tempDirs) {
    rmSync(dir, { recursive: true, force: true });
  }
});

describe("loadProvidersConfig", () => {
  it("maps snake_case YAML keys to the camelCase AppConfig shape", () => {
    const path = writeTempYaml(
      [
        "providers:",
        "  - name: openai",
        "    api_key_env: OPENAI_API_KEY",
        "    default_model: gpt-4o",
        "    models:",
        "      - name: gpt-4o",
        "        max_tokens: 4096",
        "        supports_tools: true",
        "",
      ].join("\n"),
    );

    const config = loadProvidersConfig(path);

    expect(config.providers).toHaveLength(1);
    expect(config.providers[0].name).toBe("openai");
    expect(config.providers[0].apiKeyEnv).toBe("OPENAI_API_KEY");
    expect(config.providers[0].defaultModel).toBe("gpt-4o");
    expect(config.providers[0].models[0].name).toBe("gpt-4o");
    expect(config.providers[0].models[0].maxTokens).toBe(4096);
    expect(config.providers[0].models[0].supportsTools).toBe(true);
  });

  it("throws when the YAML has no providers array", () => {
    const path = writeTempYaml("foo: bar\n");

    expect(() => loadProvidersConfig(path)).toThrow(/Invalid providers\.yaml/);
  });
});
