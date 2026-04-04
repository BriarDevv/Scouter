import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { NotificationListView } from "@/components/shared/notification-list-view";
import type { NotificationItem, NotificationListResponse } from "@/types";

vi.mock("@/lib/api/client", () => ({
  getNotifications: vi.fn(),
  updateNotificationStatus: vi.fn(),
}));

// sileo toast is a side-effect; silence it
vi.mock("sileo", () => ({
  sileo: { error: vi.fn(), success: vi.fn() },
}));

import { getNotifications } from "@/lib/api/client";

const mockGetNotifications = vi.mocked(getNotifications);

function makeItem(overrides: Partial<NotificationItem> = {}): NotificationItem {
  return {
    id: "notif-1",
    title: "Test Notification",
    message: "This is a test notification message.",
    type: "system_alert",
    severity: "info",
    category: "system",
    status: "unread",
    source_kind: null,
    channel_state: null,
    metadata: {},
    created_at: new Date().toISOString(),
    read_at: null,
    resolved_at: null,
    ...overrides,
  } as NotificationItem;
}

function makeResponse(items: NotificationItem[], total?: number): NotificationListResponse {
  return {
    items,
    total: total ?? items.length,
    page: 1,
    page_size: 25,
    unread_count: items.filter((i) => i.status === "unread").length,
  } as NotificationListResponse;
}

describe("NotificationListView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no items are returned", async () => {
    mockGetNotifications.mockResolvedValue(makeResponse([]));

    render(<NotificationListView />);

    await waitFor(() => {
      expect(screen.getByText("Sin notificaciones")).toBeInTheDocument();
    });
  });

  it("renders custom empty state title when provided", async () => {
    mockGetNotifications.mockResolvedValue(makeResponse([]));

    render(<NotificationListView emptyTitle="No hay alertas de seguridad" />);

    await waitFor(() => {
      expect(screen.getByText("No hay alertas de seguridad")).toBeInTheDocument();
    });
  });

  it("renders notification items when data exists", async () => {
    const items = [
      makeItem({ id: "1", title: "First Alert", message: "First message" }),
      makeItem({ id: "2", title: "Second Alert", message: "Second message" }),
    ];
    mockGetNotifications.mockResolvedValue(makeResponse(items));

    render(<NotificationListView />);

    await waitFor(() => {
      expect(screen.getByText("First Alert")).toBeInTheDocument();
      expect(screen.getByText("Second Alert")).toBeInTheDocument();
    });
  });

  it("shows pagination footer with item count when items exist", async () => {
    const items = [makeItem({ id: "1", title: "Alert One" })];
    mockGetNotifications.mockResolvedValue(makeResponse(items, 1));

    render(<NotificationListView />);

    await waitFor(() => {
      expect(screen.getByText("1 notificacion en total")).toBeInTheDocument();
    });
  });

  it("uses custom countLabel when provided", async () => {
    const items = [makeItem({ id: "1", title: "Security Alert" })];
    mockGetNotifications.mockResolvedValue(makeResponse(items, 1));

    render(
      <NotificationListView
        fixedCategory="security"
        countLabel={(total) => `${total} alerta(s) de seguridad`}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("1 alerta(s) de seguridad")).toBeInTheDocument();
    });
  });

  it("calls getNotifications with fixedCategory when provided", async () => {
    mockGetNotifications.mockResolvedValue(makeResponse([]));

    render(<NotificationListView fixedCategory="security" />);

    await waitFor(() => {
      expect(mockGetNotifications).toHaveBeenCalledWith(
        expect.objectContaining({ category: "security" })
      );
    });
  });

  it("calls getNotifications without category when fixedCategory is not set", async () => {
    mockGetNotifications.mockResolvedValue(makeResponse([]));

    render(<NotificationListView />);

    await waitFor(() => {
      expect(mockGetNotifications).toHaveBeenCalledWith(
        expect.objectContaining({ category: undefined })
      );
    });
  });
});
