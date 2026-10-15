import z from "zod";
import { Tool } from "../types/tools";

const tools = new Map<string, Tool>();

export function registerTool<TSchema extends z.ZodType>(
  tool: Tool<TSchema>,
): void {
  tools.set(tool.name, tool);
}

export function getTool(name: string): Tool | undefined {
  return tools.get(name);
}

export function listTools(): Tool[] {
  return Array.from(tools.values());
}
