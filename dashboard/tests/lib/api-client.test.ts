import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock constants before importing client
vi.mock("@/lib/constants", () => ({
  API_BASE_URL: "http://test-api.local",
}));

import { apiFetch } from "@/lib/api/client";

describe("apiFetch", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.useFakeTimers();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  function mockFetch(...responses: Array<Partial<Response>>) {
    const fn = globalThis.fetch as ReturnType<typeof vi.fn>;
    for (const res of responses) {
      fn.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({}),
        ...res,
      } as Response);
    }
  }

  it("makes a GET request to the correct URL", async () => {
    mockFetch({ json: async () => ({ data: "ok" }) });

    const result = await apiFetch("/leads");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://test-api.local/leads",
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      })
    );
    expect(result).toEqual({ data: "ok" });
  });

  it("returns undefined for 204 No Content", async () => {
    mockFetch({ status: 204, ok: true });

    const result = await apiFetch("/leads/1", { method: "DELETE" });

    expect(result).toBeUndefined();
  });

  it("retries GET requests on 500 errors", async () => {
    mockFetch(
      { status: 500, ok: false, statusText: "Internal Server Error" },
      { json: async () => ({ recovered: true }) }
    );

    const promise = apiFetch("/leads");
    // Advance past the retry delay (1000ms for first retry)
    await vi.advanceTimersByTimeAsync(1500);

    const result = await promise;

    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ recovered: true });
  });

  it("does not retry POST requests on 500 errors", async () => {
    mockFetch({ status: 500, ok: false, statusText: "Internal Server Error" });

    await expect(
      apiFetch("/leads", { method: "POST" })
    ).rejects.toThrow("API error: 500 Internal Server Error");

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("throws on non-retryable client errors", async () => {
    mockFetch({ status: 404, ok: false, statusText: "Not Found" });

    await expect(apiFetch("/leads/999")).rejects.toThrow(
      "API error: 404 Not Found"
    );
  });

  it("throws after exhausting all retries", async () => {
    mockFetch(
      { status: 500, ok: false, statusText: "Internal Server Error" },
      { status: 500, ok: false, statusText: "Internal Server Error" },
      { status: 500, ok: false, statusText: "Internal Server Error" }
    );

    const promise = apiFetch("/leads").catch((e: Error) => e);
    // Advance past both retry delays (1s + 2s)
    await vi.advanceTimersByTimeAsync(1500);
    await vi.advanceTimersByTimeAsync(3000);

    const error = await promise;
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toBe("API error: 500 Internal Server Error");
    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });
});
