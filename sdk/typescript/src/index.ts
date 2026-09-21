/**
 * Memex SDK — TypeScript client for Memex agent memory.
 *
 * Local-first, zero-LLM agent memory. Default retrieval path makes
 * no model API call. Memories stay on the local machine.
 *
 * @license AliceLabs Proprietary v1.0
 * @copyright 2026 AliceLabs
 */

export interface MemexConfig {
  /** Memex server URL (default: http://127.0.0.1:19420) */
  baseUrl?: string;
  /** API token for auth (if MEMEX_API_TOKEN is set on server) */
  apiToken?: string;
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

export interface Memory {
  text: string;
  score?: number;
  id?: string;
  metadata?: Record<string, unknown>;
}

export interface RecallResult {
  memories: Memory[];
  method: string;
  degraded?: boolean;
}

export interface RecallHybridResult {
  memories: Memory[];
  method: string;
}

export interface HealthStatus {
  status: string;
  count: number;
  queued?: number;
  version?: string;
  calibrated?: boolean;
  snapshot?: boolean;
}

export interface StoreResult {
  id: string;
  text: string;
  queued_total?: number;
}

export interface ExportResult {
  version: string;
  created_at: string;
  package_version: string;
  memory_count: number;
  memories: Memory[];
}

export class MemexClient {
  private baseUrl: string;
  private apiToken: string | undefined;
  private timeout: number;

  constructor(config: MemexConfig = {}) {
    this.baseUrl = config.baseUrl ?? "http://127.0.0.1:19420";
    this.apiToken = config.apiToken ?? process.env.MEMEX_API_TOKEN;
    this.timeout = config.timeout ?? 30000;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiToken) {
      headers["Authorization"] = `Bearer ${this.apiToken}`;
    }
    return headers;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        headers: { ...this.getHeaders(), ...options.headers },
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: response.statusText }));
        throw new MemexError(error.error ?? `HTTP ${response.status}`, response.status);
      }

      return await response.json() as T;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Check server health.
   * @returns Health status with memory count, queue depth, and version.
   */
  async health(): Promise<HealthStatus> {
    return this.request<HealthStatus>("/health");
  }

  /**
   * Store a memory verbatim. No LLM extraction — the agent decides content.
   * @param text The memory text to store.
   * @param id Optional memory ID (UUID).
   * @returns Store result with ID and text.
   */
  async store(text: string, id?: string): Promise<StoreResult> {
    const body: Record<string, unknown> = { text };
    if (id) body.id = id;
    return this.request<StoreResult>("/store", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /**
   * Add raw text via mem0 extraction LLM.
   * Note: This calls an LLM for extraction. Use store() for zero-LLM writes.
   * @param text Raw unstructured text to extract memories from.
   */
  async add(text: string): Promise<{ count: number; memories: string[] }> {
    return this.request<{ count: number; memories: string[] }>("/add", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  }

  /**
   * Recall memories for a query. Two-stage retrieval with optional LLM filter.
   * Zero-LLM by default.
   * @param query Natural-language query.
   * @param options.limit Max results (default: 50).
   * @param options.threshold Score threshold.
   * @param options.since ISO 8601 date filter.
   */
  async recall(
    query: string,
    options: { limit?: number; threshold?: number; since?: string } = {}
  ): Promise<RecallResult> {
    const body: Record<string, unknown> = { text: query, limit: options.limit ?? 50 };
    if (options.threshold) body.threshold = options.threshold;
    if (options.since) body.since = options.since;
    return this.request<RecallResult>("/recall", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /**
   * Hybrid recall: BM25 + dense + RRF with tiered LLM escalation.
   * Zero-LLM tier by default (83.2% R@1, $0/query).
   * @param query Natural-language query.
   * @param options.tier Retrieval tier: zero_llm | filter | flagship.
   * @param options.limit Max results.
   * @param options.topK Candidates for reranker.
   */
  async recallHybrid(
    query: string,
    options: { tier?: "zero_llm" | "filter" | "flagship"; limit?: number; topK?: number } = {}
  ): Promise<RecallHybridResult> {
    return this.request<RecallHybridResult>("/recall_hybrid", {
      method: "POST",
      body: JSON.stringify({
        text: query,
        limit: options.limit ?? 50,
        tier: options.tier ?? "zero_llm",
        top_k: options.topK ?? 5,
      }),
    });
  }

  /**
   * Simple vector query (no filter, no LLM).
   * @param query Search query.
   * @param limit Max results (default: 5).
   */
  async query(query: string, limit: number = 5): Promise<{ memories: Memory[] }> {
    return this.request<{ memories: Memory[] }>("/query", {
      method: "POST",
      body: JSON.stringify({ text: query, limit }),
    });
  }

  /**
   * Export all memories for backup.
   * No LLM call — pure vector store dump.
   */
  async export(): Promise<ExportResult> {
    return this.request<ExportResult>("/export");
  }

  /**
   * Stream recall results via Server-Sent Events.
   * @param query Natural-language query.
   * @param onMemory Callback for each memory received.
   * @param onDone Callback when stream completes.
   */
  async streamRecall(
    query: string,
    onMemory: (memory: Memory, index: number) => void,
    onDone?: (count: number, method: string, latencyMs: number) => void,
  ): Promise<void> {
    const url = `${this.baseUrl}/recall/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ text: query, limit: 20 }),
    });

    if (!response.ok || !response.body) {
      throw new MemexError(`Stream failed: HTTP ${response.status}`, response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const json = line.slice(6).trim();
          try {
            const event = JSON.parse(json);
            if (event.done) {
              onDone?.(event.count, event.method, event.total_latency_ms);
            } else if (event.memory) {
              onMemory(event.memory, event.index);
            }
          } catch {
            // skip unparseable
          }
        }
      }
    }
  }
}

export class MemexError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.name = "MemexError";
    this.statusCode = statusCode;
  }
}

/** Default export — create a client with defaults. */
export default function memex(config?: MemexConfig): MemexClient {
  return new MemexClient(config);
}
