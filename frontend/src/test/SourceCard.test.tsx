import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SourceCard from "../components/SourceCard";

// Mock react-syntax-highlighter to avoid ESM import issues in test
vi.mock("react-syntax-highlighter/dist/esm/languages/hljs/fortran", () => ({
  default: () => {},
}));

vi.mock("react-syntax-highlighter/dist/esm/styles/hljs", () => ({
  atomOneDark: {},
}));

vi.mock("react-syntax-highlighter", () => ({
  Light: Object.assign(
    ({ children }: { children: string }) => <pre data-testid="syntax-hl">{children}</pre>,
    { registerLanguage: () => {} },
  ),
}));

vi.mock("../api", () => ({
  getFileContext: vi.fn(),
}));

beforeEach(() => {
  vi.restoreAllMocks();
});

const baseSource = {
  file_path: "SRC/dgesv.f",
  routine_name: "DGESV",
  routine_type: "subroutine",
  start_line: 1,
  end_line: 55,
  score: 0.92,
  text: "      SUBROUTINE DGESV(N)\n      INTEGER N\n      END",
  language: "f77",
};

describe("SourceCard", () => {
  it("renders routine name, file path, and line range", () => {
    render(<SourceCard source={baseSource} index={0} />);
    expect(screen.getByText("DGESV")).toBeTruthy();
    expect(screen.getByText(/SRC\/dgesv\.f:1-55/)).toBeTruthy();
  });

  it("score > 0.8 renders green badge", () => {
    const { container } = render(
      <SourceCard source={{ ...baseSource, score: 0.85 }} index={0} />
    );
    const badge = container.querySelector(".bg-green-900");
    expect(badge).toBeTruthy();
    expect(badge?.textContent).toContain("85.0%");
  });

  it("score 0.6-0.8 renders yellow badge", () => {
    const { container } = render(
      <SourceCard source={{ ...baseSource, score: 0.7 }} index={0} />
    );
    const badge = container.querySelector(".bg-yellow-900");
    expect(badge).toBeTruthy();
    expect(badge?.textContent).toContain("70.0%");
  });

  it("score < 0.6 renders gray badge", () => {
    const { container } = render(
      <SourceCard source={{ ...baseSource, score: 0.5 }} index={0} />
    );
    // Gray badge — both the routine_type badge and score badge use bg-gray-700
    // Find the one containing a percentage
    const badges = container.querySelectorAll(".bg-gray-700");
    const scoreBadge = Array.from(badges).find((b) =>
      b.textContent?.includes("50.0%")
    );
    expect(scoreBadge).toBeTruthy();
  });

  it("click header toggles expand/collapse", () => {
    const { container } = render(
      <SourceCard source={baseSource} index={0} />
    );
    // Initially collapsed — no syntax highlighter
    expect(screen.queryByTestId("syntax-hl")).toBeNull();

    // Click to expand
    const header = container.querySelector(".cursor-pointer")!;
    fireEvent.click(header);
    expect(screen.getByTestId("syntax-hl")).toBeTruthy();

    // Click to collapse
    fireEvent.click(header);
    expect(screen.queryByTestId("syntax-hl")).toBeNull();
  });

  it("expanded card shows code", () => {
    render(<SourceCard source={baseSource} index={0} expanded={true} />);
    expect(screen.getByTestId("syntax-hl")).toBeTruthy();
    expect(screen.getByText(/SUBROUTINE DGESV/)).toBeTruthy();
  });

  it("view full context button calls getFileContext", async () => {
    const { getFileContext } = await import("../api");
    const mockGetFileContext = vi.mocked(getFileContext);
    mockGetFileContext.mockResolvedValue({
      file_path: "SRC/dgesv.f",
      start_line: 1,
      end_line: 100,
      total_lines: 100,
      content: "      FULL CONTEXT CODE\n",
    });

    render(<SourceCard source={baseSource} index={0} expanded={true} />);
    const contextBtn = screen.getByText("View full context");
    fireEvent.click(contextBtn);

    await waitFor(() => {
      expect(mockGetFileContext).toHaveBeenCalledWith("SRC/dgesv.f", 1, 55, 50);
    });
  });

  it("context load failure shows error message", async () => {
    const { getFileContext } = await import("../api");
    const mockGetFileContext = vi.mocked(getFileContext);
    mockGetFileContext.mockRejectedValue(new Error("Network error"));

    render(<SourceCard source={baseSource} index={0} expanded={true} />);
    const contextBtn = screen.getByText("View full context");
    fireEvent.click(contextBtn);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load file context/)).toBeTruthy();
    });
  });

  it("show snippet toggles back to original snippet", async () => {
    const { getFileContext } = await import("../api");
    const mockGetFileContext = vi.mocked(getFileContext);
    mockGetFileContext.mockResolvedValue({
      file_path: "SRC/dgesv.f",
      start_line: 1,
      end_line: 100,
      total_lines: 100,
      content: "      FULL CONTEXT CODE\n",
    });

    render(<SourceCard source={baseSource} index={0} expanded={true} />);

    // Load full context
    fireEvent.click(screen.getByText("View full context"));
    await waitFor(() => {
      expect(screen.getByText("Show snippet")).toBeTruthy();
    });

    // Toggle back
    fireEvent.click(screen.getByText("Show snippet"));
    await waitFor(() => {
      expect(screen.getByText("View full context")).toBeTruthy();
    });
  });

  it("initially collapsed by default", () => {
    render(<SourceCard source={baseSource} index={0} />);
    expect(screen.queryByTestId("syntax-hl")).toBeNull();
  });
});
