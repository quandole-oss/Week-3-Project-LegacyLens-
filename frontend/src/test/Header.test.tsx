import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Header from "../components/Header";
import * as api from "../api";

vi.mock("../api", () => ({
  getStats: vi.fn(),
}));

const mockGetStats = vi.mocked(api.getStats);

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("Header", () => {
  it("renders LegacyLens title and LAPACK Explorer badge", () => {
    mockGetStats.mockResolvedValue({
      index_name: "legacylens",
      total_vectors: 0,
      dimensions: 1536,
    });

    render(<Header />);
    expect(screen.getByText("Legacy")).toBeTruthy();
    expect(screen.getByText("Lens")).toBeTruthy();
    expect(screen.getByText("LAPACK Explorer")).toBeTruthy();
  });

  it("fetches stats on mount and displays formatted vector count", async () => {
    mockGetStats.mockResolvedValue({
      index_name: "legacylens",
      total_vectors: 5000,
      dimensions: 1536,
    });

    render(<Header />);
    await waitFor(() => {
      expect(screen.getByText("5,000 vectors indexed")).toBeTruthy();
    });
  });

  it("hides vector count before stats load", () => {
    // Stats haven't resolved yet
    mockGetStats.mockReturnValue(new Promise(() => {})); // never resolves

    render(<Header />);
    expect(screen.queryByText(/vectors indexed/)).toBeNull();
  });

  it("handles getStats rejection gracefully", async () => {
    mockGetStats.mockRejectedValue(new Error("Network error"));

    // Should not crash
    const { container } = render(<Header />);
    await waitFor(() => {
      expect(container.querySelector("header")).toBeTruthy();
    });
    expect(screen.queryByText(/vectors indexed/)).toBeNull();
  });

  it("displays stats when available after loading", async () => {
    mockGetStats.mockResolvedValue({
      index_name: "legacylens",
      total_vectors: 12345,
      dimensions: 1536,
    });

    render(<Header />);
    await waitFor(() => {
      expect(screen.getByText("12,345 vectors indexed")).toBeTruthy();
    });
  });
});
