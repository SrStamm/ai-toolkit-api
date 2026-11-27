#!/usr/bin/env node
/**
 * Non-mutating guard for the RAG contract boundary.
 *
 * The generated package may be imported only from each consumer's
 * `src/adapters/rag-contracts.ts`. Generated internals are never importable.
 */

import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const consumerRoots = ["ts-agent/src", "front-ai-toolkit/src"];
const allowedAdapter = "src/adapters/rag-contracts.ts";
const sourceExtensions = new Set([".ts", ".tsx"]);

const forbidden = [
  { label: "generated package import", pattern: /@(?:ai-toolkit|package)\/rag-contracts/ },
  { label: "generated internals import", pattern: /(?:src\/)?generated\/api(?:\.ts|\.js)?/ },
];

function collectFiles(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectFiles(path));
    } else if (sourceExtensions.has(entry.name.slice(entry.name.lastIndexOf(".")))) {
      files.push(path);
    }
  }
  return files;
}

const offenders = [];
for (const consumerRoot of consumerRoots) {
  const absoluteRoot = join(repoRoot, consumerRoot);
  for (const file of collectFiles(absoluteRoot)) {
    const repoPath = relative(repoRoot, file).replaceAll("\\", "/");
    if (repoPath.endsWith(allowedAdapter)) continue;

    const lines = readFileSync(file, "utf8").split(/\r?\n/);
    lines.forEach((line, index) => {
      for (const { label, pattern } of forbidden) {
        if (pattern.test(line)) {
          offenders.push(`${repoPath}:${index + 1}: ${label}`);
        }
      }
    });
  }
}

if (offenders.length > 0) {
  console.error("RAG contract boundary violated:");
  for (const offender of offenders) console.error(`  ${offender}`);
  console.error(
    `Only */${allowedAdapter} may import @ai-toolkit/rag-contracts.`,
  );
  process.exit(1);
}

console.log("RAG contract boundary OK: no generated contract leaks found.");
