import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ReadinessGate } from "@/components/layout/readiness-gate";

// Mock next/navigation
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/dashboard"),
  useRouter: vi.fn(() => ({ replace: mockReplace })),
}));

// Mock the API call
vi.mock("@/lib/api/client", () => ({
  getSetupReadiness: vi.fn(),
}));

import { getSetupReadiness } from "@/lib/api/client";
import { usePathname } from "next/navigation";

const mockGetSetupReadiness = vi.mocked(getSetupReadiness);
const mockUsePathname = vi.mocked(usePathname);

describe("ReadinessGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue("/dashboard");
  });

  it("renders children when dashboard_unlocked is true", async () => {
    mockGetSetupReadiness.mockResolvedValue({
      dashboard_unlocked: true,
      has_smtp: true,
      has_leads: true,
    } as any);

    render(
      <ReadinessGate>
        <div>Protected Content</div>
      </ReadinessGate>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("redirects to /onboarding when dashboard_unlocked is false", async () => {
    mockGetSetupReadiness.mockResolvedValue({
      dashboard_unlocked: false,
      has_smtp: false,
      has_leads: false,
    } as any);

    render(
      <ReadinessGate>
        <div>Protected Content</div>
      </ReadinessGate>
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/onboarding?next=%2Fdashboard"
      );
    });
  });

  it("shows loading indicator while checking readiness", () => {
    // Never resolves so we stay in loading state
    mockGetSetupReadiness.mockReturnValue(new Promise(() => {}));

    render(
      <ReadinessGate>
        <div>Protected Content</div>
      </ReadinessGate>
    );

    expect(screen.getByText(/Validando estado inicial/)).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children on allowed paths even while locked", async () => {
    mockUsePathname.mockReturnValue("/onboarding");
    mockGetSetupReadiness.mockResolvedValue({
      dashboard_unlocked: false,
      has_smtp: false,
      has_leads: false,
    } as any);

    render(
      <ReadinessGate>
        <div>Onboarding Content</div>
      </ReadinessGate>
    );

    // /onboarding is in ALLOWED_WHILE_LOCKED — loading spinner should not block it
    await waitFor(() => {
      expect(screen.getByText("Onboarding Content")).toBeInTheDocument();
    });
  });

  it("renders children when API call fails", async () => {
    mockGetSetupReadiness.mockRejectedValue(new Error("API error"));

    render(
      <ReadinessGate>
        <div>Protected Content</div>
      </ReadinessGate>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });
});
