import { ToolError, ToolErrorCode, ToolErrorCodes, ToolResult } from "./tools";

export const MAX_ERROR_MESSAGE_LENGTH = 500;

export class HttpToolError extends Error {
  constructor(
    readonly status: number,
    readonly code: ToolErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "HttpToolError";
  }
}

export const toCodeError = (response: { status: number }): ToolErrorCode => {
  return response.status === 429
    ? ToolErrorCodes.RATE_LIMITED
    : response.status >= 500
      ? ToolErrorCodes.HTTP_5XX
      : response.status === 400
        ? ToolErrorCodes.BAD_REQUEST
        : response.status === 404
          ? ToolErrorCodes.NOT_FOUND
          : ToolErrorCodes.HTTP_4XX;
};

export const sanitizeMessage = (err: unknown): string => {
  const raw = err instanceof Error ? err.message : String(err);
  let clean = raw.split("\n")[0].replace(/\s+/g, " ").trim();
  clean = clean.replace(/https?:\/\/\S+/g, "[url]");
  return clean.length > MAX_ERROR_MESSAGE_LENGTH
    ? `${clean.slice(0, MAX_ERROR_MESSAGE_LENGTH)}...`
    : clean;
};

export const toToolError = (
  toolName: string,
  err: unknown,
  timedOut: boolean,
  forced?: {
    code?: ToolErrorCode;
    retryable?: boolean;
  },
): ToolError => {
  const classify = (): Pick<ToolError, "code" | "retryable"> => {
    if (timedOut === true) {
      return { code: ToolErrorCodes.TIMEOUT, retryable: true };
    }

    // err.status === 429 || err.status >= 500
    if (err instanceof HttpToolError) {
      return {
        code: err.code,
        retryable: err.status === 429 || err.status >= 500,
      };
    }

    // Network/fetch error | NETWORK_ERROR | yes
    if (err instanceof TypeError) {
      return { code: ToolErrorCodes.NETWORK_ERROR, retryable: true };
    }

    return { code: ToolErrorCodes.UNKNOWN, retryable: false };
  };

  const classified = classify();

  return {
    toolName: toolName,
    code: forced?.code ?? classified.code,
    message: sanitizeMessage(err),
    retryable: forced?.retryable ?? classified.retryable,
    timestamp: Date.now(),
  };
};

export const isToolResult = (value: unknown): value is ToolResult => {
  if (typeof value !== "object" || value === null || !("ok" in value))
    return false;

  if (value.ok === true) {
    return (
      "output" in value &&
      typeof value.output === "string" &&
      "metadata" in value &&
      typeof value.metadata === "object" &&
      value.metadata !== null
    );
  }

  return (
    value.ok === false &&
    "error" in value &&
    typeof value.error === "string" &&
    "retryable" in value &&
    typeof value.retryable === "boolean"
  );
};
