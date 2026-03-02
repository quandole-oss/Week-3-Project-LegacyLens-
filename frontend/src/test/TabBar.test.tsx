import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TabBar from "../components/TabBar";

describe("TabBar", () => {
  it("renders all 7 tabs", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    expect(screen.getByText("Ask")).toBeTruthy();
    expect(screen.getByText("Search")).toBeTruthy();
    expect(screen.getByText("Explain")).toBeTruthy();
    expect(screen.getByText("Docs")).toBeTruthy();
    expect(screen.getByText("Deps")).toBeTruthy();
    expect(screen.getByText("Patterns")).toBeTruthy();
    expect(screen.getByText("Logic")).toBeTruthy();
  });

  it("highlights the active tab with indigo background", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    const askButton = screen.getByText("Ask");
    expect(askButton.className).toContain("bg-indigo-600");
  });

  it("does not highlight inactive tabs", () => {
    render(<TabBar activeTab="query" onTabChange={() => {}} />);
    const searchButton = screen.getByText("Search");
    expect(searchButton.className).not.toContain("bg-indigo-600");
  });

  it("calls onTabChange with correct tab id when clicked", () => {
    const handleChange = vi.fn();
    render(<TabBar activeTab="query" onTabChange={handleChange} />);

    fireEvent.click(screen.getByText("Search"));
    expect(handleChange).toHaveBeenCalledWith("search");

    fireEvent.click(screen.getByText("Explain"));
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
