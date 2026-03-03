import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TabBar from "../components/TabBar";

describe("TabBar", () => {
  it("renders all 7 tabs", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    expect(screen.getByText("[ ASK ]")).toBeTruthy();
    expect(screen.getByText(/SEARCH/)).toBeTruthy();
    expect(screen.getByText(/EXPLAIN/)).toBeTruthy();
    expect(screen.getByText(/DOCS/)).toBeTruthy();
    expect(screen.getByText(/DEPS/)).toBeTruthy();
    expect(screen.getByText(/PATTERNS/)).toBeTruthy();
    expect(screen.getByText(/LOGIC/)).toBeTruthy();
  });

  it("highlights the active tab with phosphor background", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    const askButton = screen.getByText("[ ASK ]");
    expect(askButton.className).toContain("bg-phosphor");
  });

  it("does not highlight inactive tabs", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    const searchButton = screen.getByText(/SEARCH/);
    // Inactive tabs use bg-transparent; active uses bg-phosphor (without hover:)
    expect(searchButton.className).toContain("bg-transparent");
  });

  it("calls onTabChange with correct tab id when clicked", () => {
    const handleChange = vi.fn();
    render(<TabBar activeTab="query" onTabChange={handleChange} />);

    fireEvent.click(screen.getByText(/SEARCH/));
    expect(handleChange).toHaveBeenCalledWith("search");

    fireEvent.click(screen.getByText(/EXPLAIN/));
    expect(handleChange).toHaveBeenCalledWith("explain");
  });

  it("has flex-wrap for responsive layout", () => {
    const { container } = render(
      <TabBar activeTab="query" onTabChange={() => {}} />
    );
    const tabContainer = container.firstChild as HTMLElement;
    expect(tabContainer.className).toContain("flex-wrap");
  });
});
