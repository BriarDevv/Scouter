import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "@/components/shared/stat-card";
import { Activity } from "lucide-react";

// next/link uses anchor tags in test environment
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Total Leads" value={42} />);

    expect(screen.getByText("Total Leads")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders change indicator when provided", () => {
    render(
      <StatCard
        label="Leads"
        value={100}
        change="+12%"
        changeType="positive"
      />
    );

    expect(screen.getByText("+12%")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(
      <StatCard label="Leads" value={100} subtitle="vs last week" />
    );

    expect(screen.getByText("vs last week")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(
      <StatCard label="Activity" value={5} icon={Activity} />
    );

    // lucide-react renders an SVG element
    const svg = document.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("renders without optional props", () => {
    render(<StatCard label="Simple" value="N/A" />);

    expect(screen.getByText("Simple")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("wraps content in a link when href is provided", () => {
    render(<StatCard label="Linked" value={10} href="/leads" />);

    const link = document.querySelector('a[href="/leads"]');
    expect(link).toBeTruthy();
  });
});
