import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { AnswerSkeleton, SourceSkeleton } from "../components/Skeleton";

describe("AnswerSkeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(<AnswerSkeleton />);
    expect(container.firstChild).toBeTruthy();
  });

  it("has animate-pulse class for loading animation", () => {
    const { container } = render(<AnswerSkeleton />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders placeholder lines", () => {
    const { container } = render(<AnswerSkeleton />);
    // Should have multiple placeholder bars (bg-gray-700 rounded divs)
    const bars = container.querySelectorAll(".bg-gray-700.rounded");
    expect(bars.length).toBeGreaterThanOrEqual(3);
  });
});

describe("SourceSkeleton", () => {
  it("renders default 3 skeleton cards", () => {
    const { container } = render(<SourceSkeleton />);
    const cards = container.querySelectorAll(".bg-gray-800");
    expect(cards.length).toBe(3);
  });

  it("renders specified number of cards", () => {
    const { container } = render(<SourceSkeleton count={5} />);
    const cards = container.querySelectorAll(".bg-gray-800");
    expect(cards.length).toBe(5);
  });

  it("has animate-pulse on cards", () => {
    const { container } = render(<SourceSkeleton count={2} />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThanOrEqual(2);
  });
});
