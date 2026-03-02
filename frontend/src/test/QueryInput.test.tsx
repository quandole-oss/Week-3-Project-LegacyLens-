import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import QueryInput from "../components/QueryInput";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("QueryInput", () => {
  it("renders input field and Ask button", () => {
    render(<QueryInput onSubmit={() => {}} isLoading={false} />);
    expect(screen.getByPlaceholderText("Ask about LAPACK code...")).toBeTruthy();
    expect(screen.getByText("Ask")).toBeTruthy();
  });

  it("submit button disabled when input is empty", () => {
    render(<QueryInput onSubmit={() => {}} isLoading={false} />);
    const button = screen.getByText("Ask");
    expect(button).toBeDisabled();
  });

  it("submit button disabled when isLoading", () => {
    render(<QueryInput onSubmit={() => {}} isLoading={true} />);
    const input = screen.getByPlaceholderText("Ask about LAPACK code...");
    fireEvent.change(input, { target: { value: "test query" } });
    // Find the submit button - when loading, it shows "Thinking..."
    const button = screen.getByText("Thinking...");
    expect(button.closest("button")).toBeDisabled();
  });

  it("form submission calls onSubmit with trimmed query", () => {
    const handleSubmit = vi.fn();
    render(<QueryInput onSubmit={handleSubmit} isLoading={false} />);
    const input = screen.getByPlaceholderText("Ask about LAPACK code...");
    fireEvent.change(input, { target: { value: "  What is DGESV?  " } });
    fireEvent.submit(input.closest("form")!);
    expect(handleSubmit).toHaveBeenCalledWith("What is DGESV?");
  });

  it("enter key submits form", () => {
    const handleSubmit = vi.fn();
    render(<QueryInput onSubmit={handleSubmit} isLoading={false} />);
    const input = screen.getByPlaceholderText("Ask about LAPACK code...");
    fireEvent.change(input, { target: { value: "DGESV" } });
    fireEvent.submit(input.closest("form")!);
    expect(handleSubmit).toHaveBeenCalledWith("DGESV");
  });

  it("renders all 5 example query buttons", () => {
    render(<QueryInput onSubmit={() => {}} isLoading={false} />);
    expect(screen.getByText("What does DGESV do?")).toBeTruthy();
    expect(screen.getByText("How does LU decomposition work in LAPACK?")).toBeTruthy();
    expect(screen.getByText("Find routines that solve eigenvalue problems")).toBeTruthy();
    expect(screen.getByText("Explain the BLAS matrix multiplication routine")).toBeTruthy();
    expect(screen.getByText("What are the dependencies of DGEEV?")).toBeTruthy();
  });

  it("clicking example button calls onSubmit immediately", () => {
    const handleSubmit = vi.fn();
    render(<QueryInput onSubmit={handleSubmit} isLoading={false} />);
    fireEvent.click(screen.getByText("What does DGESV do?"));
    expect(handleSubmit).toHaveBeenCalledWith("What does DGESV do?");
  });

  it("example buttons disabled when isLoading", () => {
    render(<QueryInput onSubmit={() => {}} isLoading={true} />);
    const exampleButton = screen.getByText("What does DGESV do?");
    expect(exampleButton).toBeDisabled();
  });

  it("custom placeholder prop renders", () => {
    render(
      <QueryInput
        onSubmit={() => {}}
        isLoading={false}
        placeholder="Custom placeholder..."
      />
    );
    expect(screen.getByPlaceholderText("Custom placeholder...")).toBeTruthy();
  });
});
