import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "@/components/layout/page-header";

describe("PageHeader", () => {
  it("renders the title", () => {
    render(<PageHeader title="Dashboard" />);

    expect(
      screen.getByRole("heading", { name: "Dashboard" })
    ).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <PageHeader title="Leads" description="Manage your leads" />
    );

    expect(screen.getByText("Manage your leads")).toBeInTheDocument();
  });

  it("does not render description when not provided", () => {
    render(<PageHeader title="Leads" />);

    const heading = screen.getByRole("heading", { name: "Leads" });
    // The description paragraph should not be present
    expect(heading.parentElement?.querySelector("p")).toBeNull();
  });

  it("renders action buttons passed as children", () => {
    render(
      <PageHeader title="Settings">
        <button>Save</button>
      </PageHeader>
    );

    expect(
      screen.getByRole("button", { name: "Save" })
    ).toBeInTheDocument();
  });

  it("does not render the actions container when no children", () => {
    const { container } = render(<PageHeader title="Empty" />);

    // Only one direct child div (the title block), no actions wrapper
    const wrapper = container.firstElementChild;
    expect(wrapper?.children).toHaveLength(1);
  });
});
