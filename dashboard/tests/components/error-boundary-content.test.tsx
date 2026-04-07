import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorBoundaryContent from "@/components/shared/error-boundary-content";

describe("ErrorBoundaryContent", () => {
  it("renders the error message", () => {
    const error = new Error("Something went wrong");
    render(<ErrorBoundaryContent error={error} reset={vi.fn()} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders fallback message when error.message is empty", () => {
    const error = new Error("");
    render(<ErrorBoundaryContent error={error} reset={vi.fn()} />);

    expect(
      screen.getByText("Se produjo un error inesperado.")
    ).toBeInTheDocument();
  });

  it("has a retry button", () => {
    const error = new Error("fail");
    render(<ErrorBoundaryContent error={error} reset={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: "Reintentar" })
    ).toBeInTheDocument();
  });

  it("calls reset when the retry button is clicked", async () => {
    const reset = vi.fn();
    const error = new Error("fail");
    render(<ErrorBoundaryContent error={error} reset={reset} />);

    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(reset).toHaveBeenCalledOnce();
  });
});
