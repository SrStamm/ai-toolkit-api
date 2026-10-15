type LogLevel = "debug" | "info" | "warn" | "error";

interface LogContext {
  [key: string]: unknown;
}

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const MIN_LEVEL: LogLevel = (process.env.LOG_LEVEL as LogLevel) || "info";

function shouldLog(level: LogLevel): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[MIN_LEVEL];
}

function formatTimestamp(): string {
  return new Date().toISOString();
}

function emit(level: LogLevel, component: string, message: string, ctx?: LogContext): void {
  if (!shouldLog(level)) return;

  const entry = {
    ts: formatTimestamp(),
    level,
    component,
    msg: message,
    ...ctx,
  };

  const line = JSON.stringify(entry);

  if (level === "error") {
    process.stderr.write(line + "\n");
  } else {
    process.stdout.write(line + "\n");
  }
}

export interface Logger {
  debug(msg: string, ctx?: LogContext): void;
  info(msg: string, ctx?: LogContext): void;
  warn(msg: string, ctx?: LogContext): void;
  error(msg: string, ctx?: LogContext): void;
  child(component: string): Logger;
}

function createLogger(component: string): Logger {
  return {
    debug: (msg, ctx) => emit("debug", component, msg, ctx),
    info: (msg, ctx) => emit("info", component, msg, ctx),
    warn: (msg, ctx) => emit("warn", component, msg, ctx),
    error: (msg, ctx) => emit("error", component, msg, ctx),
    child: (sub) => createLogger(`${component}:${sub}`),
  };
}

export const logger = createLogger("ts-agent");
