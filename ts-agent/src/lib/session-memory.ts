// Create Redis client
import { Redis } from "ioredis";
import { Message } from "../types/llm";

const REDIS_URL = process.env.REDIS_URL;
export const redisClient = new Redis(REDIS_URL || "redis://localhost:6379", {
  retryStrategy(times) {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
});

interface SessionMemoryConfig {
  defaultWindowSize: number;
  defaultTTLSeconds: number;
}

// Create class for Session Memory
export class SessionMemory {
  private client: Redis;
  private windowSize: number;
  private ttlSeconds: number;

  constructor(client: Redis, config?: SessionMemoryConfig) {
    this.client = client;
    this.windowSize = config?.defaultWindowSize ?? 5;
    this.ttlSeconds = config?.defaultTTLSeconds ?? 10800;
  }

  private generateKey(sessionId: string) {
    return `session:${sessionId}`;
  }

  async add(sessionId: string, message: Message): Promise<void> {
    const key = this.generateKey(sessionId);

    try {
      await this.client
        .pipeline()
        .lpush(key, JSON.stringify(message)) // Save the message
        .ltrim(key, 0, this.windowSize - 1) // Trim to window size
        .expire(key, this.ttlSeconds) // Refresh TTL
        .exec();
    } catch (err) {
      console.error(
        `[SessionMemory] Error guardando mensaje para ${sessionId}:`,
        err,
      );
    }
  }

  async getHistory(sessionId: string): Promise<Message[] | []> {
    const key = this.generateKey(sessionId);

    try {
      // Get all messages in the list
      const rawMessages = await this.client.lrange(key, 0, -1);

      if (!rawMessages) return [];

      return rawMessages.map((m) => JSON.parse(m)).reverse();
    } catch (err) {
      console.error(
        `[SessionMemory] Error obteniendo historial para ${sessionId}:`,
        err,
      );
      return [];
    }
  }

  async clear(sessionId: string) {
    const key = this.generateKey(sessionId);
    const result = await this.client.del(key);
    return result > 0;
  }

  async exists(sessionId: string): Promise<boolean> {
    const key = this.generateKey(sessionId);
    const result = await this.client.exists(key);
    return result === 1;
  }

  async getTTL(sessionId: string) {
    const key = this.generateKey(sessionId);
    return await this.client.ttl(key);
  }
}
