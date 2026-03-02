import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * Tests for the SSE streaming logic in api.ts.
 * We test the streamQuery generator by mocking fetch to return
 * a ReadableStream with controlled chunks.
 */

// Helper to create a ReadableStream from string chunks
function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("streamQuery", () => {
  it("yields parsed SSE events from stream", async () => {
    const mockResponse = {
      ok: true,
      body: makeStream([
        'data: {"type":"sources","data":[]}\n\n',
        'data: {"type":"token","data":"Hello"}\n\n',
        'data: {"type":"done"}\n\n',
      ]),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    // Dynamic import to pick up the mocked fetch
    const { streamQuery } = await import("../api");

    const events = [];
    for await (const event of streamQuery("/api/query", "test")) {
      events.push(event);
    }

    expect(events).toHaveLength(3);
    expect(events[0].type).toBe("sources");
    expect(events[1].type).toBe("token");
    expect(events[1].data).toBe("Hello");
    expect(events[2].type).toBe("done");
  });

  it("handles chunked data split across reads", async () => {
    // Simulate a data line split across two read() calls
    const mockResponse = {
      ok: true,
      body: makeStream([
        'data: {"type":"toke',
        'n","data":"Hi"}\n\n',
      ]),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { streamQuery } = await import("../api");

    const events = [];
    for await (const event of streamQuery("/api/query", "test")) {
      events.push(event);
    }

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe("token");
    expect(events[0].data).toBe("Hi");
  });

  it("processes remaining buffer after stream ends", async () => {
    // Final chunk has no trailing newline — tests the buffer flush fix
    const mockResponse = {
      ok: true,
      body: makeStream([
        'data: {"type":"token","data":"first"}\n\n',
        'data: {"type":"done"}',  // No trailing \n\n
      ]),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { streamQuery } = await import("../api");

    const events = [];
    for await (const event of streamQuery("/api/query", "test")) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(events[0].type).toBe("token");
    expect(events[1].type).toBe("done");
  });

  it("skips malformed events", async () => {
    const mockResponse = {
      ok: true,
      body: makeStream([
        'data: not-json\n\n',
        'data: {"type":"done"}\n\n',
      ]),
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { streamQuery } = await import("../api");

    const events = [];
    for await (const event of streamQuery("/api/query", "test")) {
      events.push(event);
    }

    // Malformed event should be skipped, only "done" should come through
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe("done");
  });

  it("throws on non-ok response", async () => {
    const mockResponse = {
      ok: false,
      statusText: "Internal Server Error",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { streamQuery } = await import("../api");

    await expect(async () => {
      for await (const _ of streamQuery("/api/query", "test")) {
        // consume
      }
    }).rejects.toThrow("Request failed");
  });

  it("throws when response body is null", async () => {
    const mockResponse = {
      ok: true,
      body: null,
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse));

    const { streamQuery } = await import("../api");

    await expect(async () => {
      for await (const _ of streamQuery("/api/query", "test")) {
        // consume
      }
    }).rejects.toThrow("No response body");
  });
});

describe("searchCode", () => {
  it("sends POST to /api/search and returns parsed results", async () => {
    const mockData = {
      query: "DGESV",
      results: [
        {
          text: "SUBROUTINE DGESV",
          file_path: "SRC/dgesv.f",
          routine_name: "DGESV",
          routine_type: "subroutine",
          start_line: 1,
          end_line: 55,
          language: "f77",
          score: 0.95,
        },
      ],
      count: 1,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })
    );

    const { searchCode } = await import("../api");
    const result = await searchCode("DGESV", 5);

    expect(result.query).toBe("DGESV");
    expect(result.results).toHaveLength(1);
    expect(result.results[0].routine_name).toBe("DGESV");
    expect(result.count).toBe(1);

    const fetchCall = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(fetchCall[0]).toContain("/api/search");
    const body = JSON.parse(fetchCall[1].body);
    expect(body.query).toBe("DGESV");
    expect(body.top_k).toBe(5);
  });

  it("handles fetch error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Server Error",
      })
    );

    const { searchCode } = await import("../api");
    await expect(searchCode("test")).rejects.toThrow("Search failed");
  });
});

describe("getStats", () => {
  it("sends GET to /api/stats and returns IndexStats", async () => {
    const mockStats = {
      index_name: "legacylens",
      total_vectors: 5000,
      dimensions: 1536,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockStats),
      })
    );

    const { getStats } = await import("../api");
    const stats = await getStats();

    expect(stats.index_name).toBe("legacylens");
    expect(stats.total_vectors).toBe(5000);
    expect(stats.dimensions).toBe(1536);

    const fetchCall = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(fetchCall[0]).toContain("/api/stats");
  });

  it("handles fetch error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        statusText: "Internal Server Error",
      })
    );

    const { getStats } = await import("../api");
    await expect(getStats()).rejects.toThrow("Stats failed");
  });
});

describe("getFileContext", () => {
  it("sends POST to /api/file-context with correct params", async () => {
    const mockContext = {
      file_path: "SRC/dgesv.f",
      start_line: 1,
      end_line: 100,
      total_lines: 100,
      content: "      SUBROUTINE DGESV\n",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockContext),
      })
    );

    const { getFileContext } = await import("../api");
    const ctx = await getFileContext("SRC/dgesv.f", 10, 20, 30);

    expect(ctx.file_path).toBe("SRC/dgesv.f");
    expect(ctx.content).toContain("SUBROUTINE DGESV");

    const fetchCall = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(fetchCall[1].body);
    expect(body.file_path).toBe("SRC/dgesv.f");
    expect(body.start_line).toBe(10);
    expect(body.end_line).toBe(20);
    expect(body.context_lines).toBe(30);
  });

  it("default contextLines is 50", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            file_path: "test.f",
            start_line: 1,
            end_line: 100,
            total_lines: 100,
            content: "",
          }),
      })
    );

    const { getFileContext } = await import("../api");
    await getFileContext("test.f", 1, 10);

    const fetchCall = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(fetchCall[1].body);
    expect(body.context_lines).toBe(50);
  });
});
