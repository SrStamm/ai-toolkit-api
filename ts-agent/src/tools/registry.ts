import { Tool } from "../types/tools";

const tools = new Map<string, Tool>();

export function registerTool(tool: Tool) {
  tools.set(tool.name, tool);
}

export function getTool(name: string): Tool | undefined {
  return tools.get(name);
}

export function listTools(): Tool[] {
  return Array.from(tools.values());
}
