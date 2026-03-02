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
