import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AnswerPanel from "../components/AnswerPanel";

describe("AnswerPanel", () => {
  it("returns null when answer is empty", () => {
    const { container } = render(
      <AnswerPanel answer="" isStreaming={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders answer text", () => {
    render(<AnswerPanel answer="DGESV solves a linear system." isStreaming={false} />);
    expect(screen.getByText(/DGESV solves a linear system/)).toBeTruthy();
  });

  it("shows '=== OUTPUT ===' heading", () => {
    render(<AnswerPanel answer="Some answer" isStreaming={false} />);
    expect(screen.getByText("=== OUTPUT ===")).toBeTruthy();
  });

  it("shows streaming indicator when isStreaming is true", () => {
    render(<AnswerPanel answer="Partial..." isStreaming={true} />);
    expect(screen.getByText("GENERATING...")).toBeTruthy();
  });

  it("hides streaming indicator when isStreaming is false", () => {
    render(<AnswerPanel answer="Complete answer" isStreaming={false} />);
    expect(screen.queryByText("GENERATING...")).toBeNull();
  });

  it("renders markdown content", () => {
    render(
      <AnswerPanel answer="**bold text** and *italic*" isStreaming={false} />
    );
    const bold = document.querySelector("strong");
    expect(bold).toBeTruthy();
    expect(bold?.textContent).toBe("bold text");
  });
});
