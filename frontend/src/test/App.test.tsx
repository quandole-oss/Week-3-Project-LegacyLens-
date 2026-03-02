import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import type { StreamEvent } from "../api";

// Mock all child components to isolate App logic
vi.mock("../components/Header", () => ({
  default: () => <div data-testid="header">Header</div>,
}));

vi.mock("../components/TabBar", () => ({
  default: ({ activeTab, onTabChange }: { activeTab: string; onTabChange: (tab: string) => void }) => (
    <div data-testid="tabbar">
      <button data-testid="tab-query" onClick={() => onTabChange("query")}>Ask</button>
      <button data-testid="tab-search" onClick={() => onTabChange("search")}>Search</button>
      <button data-testid="tab-explain" onClick={() => onTabChange("explain")}>Explain</button>
      <span data-testid="active-tab">{activeTab}</span>
    </div>
  ),
}));

vi.mock("../components/QueryInput", () => ({
  default: ({
    onSubmit,
    isLoading,
    placeholder,
  }: {
    onSubmit: (q: string) => void;
    isLoading: boolean;
    placeholder?: string;
  }) => (
    <div data-testid="query-input">
      <input
        data-testid="input"
        placeholder={placeholder}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit((e.target as HTMLInputElement).value);
        }}
      />
      <button data-testid="submit" disabled={isLoading} onClick={() => onSubmit("test query")}>
        Submit
      </button>
      {isLoading && <span data-testid="loading">Loading...</span>}
    </div>
  ),
}));

vi.mock("../components/AnswerPanel", () => ({
  default: ({ answer, isStreaming }: { answer: string; isStreaming: boolean }) =>
    answer ? (
      <div data-testid="answer-panel">
        <span data-testid="answer-text">{answer}</span>
        {isStreaming && <span data-testid="streaming">Streaming...</span>}
      </div>
    ) : null,
}));

vi.mock("../components/SourceCard", () => ({
  default: ({ source, index }: { source: { routine_name: string }; index: number }) => (
    <div data-testid={`source-card-${index}`}>{source.routine_name}</div>
  ),
}));

vi.mock("../components/Skeleton", () => ({
  AnswerSkeleton: () => <div data-testid="answer-skeleton">Loading answer...</div>,
  SourceSkeleton: () => <div data-testid="source-skeleton">Loading sources...</div>,
}));

vi.mock("../api", () => ({
  streamQuery: vi.fn(),
  searchCode: vi.fn(),
}));

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders header, tabs, and query input", () => {
    render(<App />);
    expect(screen.getByTestId("header")).toBeTruthy();
    expect(screen.getByTestId("tabbar")).toBeTruthy();
    expect(screen.getByTestId("query-input")).toBeTruthy();
  });

  it("shows empty state when no query submitted", () => {
    render(<App />);
    expect(screen.getByText("Explore LAPACK Legacy Code")).toBeTruthy();
  });

  it("defaults to query tab", () => {
    render(<App />);
    expect(screen.getByTestId("active-tab").textContent).toBe("query");
  });

  it("switches tabs when tab clicked", () => {
    render(<App />);
    fireEvent.click(screen.getByTestId("tab-search"));
    expect(screen.getByTestId("active-tab").textContent).toBe("search");
  });

  it("updates placeholder when switching tabs", () => {
    render(<App />);
    // Default query tab placeholder
    expect(screen.getByTestId("input").getAttribute("placeholder")).toContain("Ask a question");

    // Switch to search tab
    fireEvent.click(screen.getByTestId("tab-search"));
    expect(screen.getByTestId("input").getAttribute("placeholder")).toContain("Search for code");
  });

  it("handles search tab query via searchCode", async () => {
    const { searchCode } = await import("../api");
    const mockSearchCode = vi.mocked(searchCode);
    mockSearchCode.mockResolvedValue({
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
    });

    render(<App />);
    fireEvent.click(screen.getByTestId("tab-search"));
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByText("Results (1)")).toBeTruthy();
      expect(screen.getByTestId("source-card-0")).toBeTruthy();
    });
  });

  it("handles streaming query with sources and tokens", async () => {
    const { streamQuery } = await import("../api");
    const mockStreamQuery = vi.mocked(streamQuery);

    async function* fakeStream() {
      yield {
        type: "sources" as const,
        data: [
          {
            file_path: "SRC/dgesv.f",
            routine_name: "DGESV",
            routine_type: "subroutine",
            start_line: 1,
            end_line: 55,
            score: 0.9,
          },
        ],
      };
      yield { type: "token" as const, data: "DGESV solves " };
      yield { type: "token" as const, data: "linear systems." };
      yield { type: "done" as const, data: undefined };
    }

    mockStreamQuery.mockReturnValue(fakeStream());

    render(<App />);
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByTestId("answer-text").textContent).toBe(
        "DGESV solves linear systems."
      );
      expect(screen.getByText("Sources (1)")).toBeTruthy();
      expect(screen.getByTestId("source-card-0")).toBeTruthy();
    });
  });

  it("shows error state on query failure", async () => {
    const { streamQuery } = await import("../api");
    const mockStreamQuery = vi.mocked(streamQuery);

    async function* failingStream(): AsyncGenerator<StreamEvent> {
      throw new Error("Network timeout");
    }

    mockStreamQuery.mockReturnValue(failingStream());

    render(<App />);
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByText("Network timeout")).toBeTruthy();
    });
  });

  it("shows error event from SSE stream", async () => {
    const { streamQuery } = await import("../api");
    const mockStreamQuery = vi.mocked(streamQuery);

    async function* errorStream() {
      yield { type: "error" as const, data: "No matching routines found" };
      yield { type: "done" as const, data: undefined };
    }

    mockStreamQuery.mockReturnValue(errorStream());

    render(<App />);
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByText("No matching routines found")).toBeTruthy();
    });
  });

  it("clears previous results when starting new query", async () => {
    const { streamQuery } = await import("../api");
    const mockStreamQuery = vi.mocked(streamQuery);

    // First query
    async function* firstStream() {
      yield {
        type: "sources" as const,
        data: [
          {
            file_path: "SRC/dgesv.f",
            routine_name: "DGESV",
            routine_type: "subroutine",
            start_line: 1,
            end_line: 55,
            score: 0.9,
          },
        ],
      };
      yield { type: "token" as const, data: "first answer" };
      yield { type: "done" as const, data: undefined };
    }

    mockStreamQuery.mockReturnValue(firstStream());
    render(<App />);
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByTestId("answer-text").textContent).toBe("first answer");
    });

    // Second query — new stream
    async function* secondStream() {
      yield { type: "token" as const, data: "second answer" };
      yield { type: "done" as const, data: undefined };
    }

    mockStreamQuery.mockReturnValue(secondStream());
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      expect(screen.getByTestId("answer-text").textContent).toBe("second answer");
    });
    // Sources should be cleared
    expect(screen.queryByText("Sources")).toBeNull();
  });

  it("handles structured data events (patterns, dependencies)", async () => {
    const { streamQuery } = await import("../api");
    const mockStreamQuery = vi.mocked(streamQuery);

    async function* depsStream() {
      yield {
        type: "dependencies" as const,
        data: { DGESV: ["DGETRF", "DGETRS"] },
      };
      yield { type: "done" as const, data: undefined };
    }

    mockStreamQuery.mockReturnValue(depsStream());

    render(<App />);
    fireEvent.click(screen.getByTestId("tab-explain"));
    fireEvent.click(screen.getByTestId("submit"));

    await waitFor(() => {
      // Structured data rendered as JSON block
      const answerText = screen.getByTestId("answer-text").textContent!;
      expect(answerText).toContain("DGESV");
      expect(answerText).toContain("DGETRF");
    });
  });
});
