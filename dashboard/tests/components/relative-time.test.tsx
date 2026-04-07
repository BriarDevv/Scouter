import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { RelativeTime } from "@/components/shared/relative-time";

describe("RelativeTime", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders "Ahora" for a timestamp less than a minute ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:30Z"));

    render(<RelativeTime date="2025-06-15T12:00:00Z" />);

    expect(screen.getByText("Ahora")).toBeInTheDocument();
  });

  it("renders minutes-ago format for recent timestamps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:05:00Z"));

    render(<RelativeTime date="2025-06-15T12:00:00Z" />);

    expect(screen.getByText("Hace 5m")).toBeInTheDocument();
  });

  it("renders hours-ago format for timestamps hours old", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T15:00:00Z"));

    render(<RelativeTime date="2025-06-15T12:00:00Z" />);

    expect(screen.getByText("Hace 3h")).toBeInTheDocument();
  });

  it("renders days-ago format for timestamps days old", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-17T12:00:00Z"));

    render(<RelativeTime date="2025-06-15T12:00:00Z" />);

    expect(screen.getByText("Hace 2d")).toBeInTheDocument();
  });

  it("renders a <time> element with correct dateTime attribute", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:30Z"));

    render(<RelativeTime date="2025-06-15T12:00:00Z" />);

    const timeEl = screen.getByText("Ahora");
    expect(timeEl.tagName).toBe("TIME");
    expect(timeEl.getAttribute("dateTime")).toBe("2025-06-15T12:00:00.000Z");
  });
});
