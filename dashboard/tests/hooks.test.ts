import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePageData } from "@/lib/hooks/use-page-data";

describe("usePageData", () => {
  it("returns loading=true initially", () => {
    const fetcher = vi.fn(() => new Promise(() => {})); // never resolves
    const { result } = renderHook(() => usePageData(fetcher));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("sets data and loading=false after fetcher resolves", async () => {
    const mockData = { id: 1, name: "Test" };
    const fetcher = vi.fn().mockResolvedValue(mockData);

    const { result } = renderHook(() => usePageData(fetcher));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("sets error and loading=false when fetcher rejects", async () => {
    const fetchError = new Error("Network failure");
    const fetcher = vi.fn().mockRejectedValue(fetchError);

    const { result } = renderHook(() => usePageData(fetcher));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Network failure");
    expect(result.current.data).toBeNull();
  });

  it("wraps non-Error rejections in an Error", async () => {
    const fetcher = vi.fn().mockRejectedValue("plain string error");

    const { result } = renderHook(() => usePageData(fetcher));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("plain string error");
  });

  it("refresh re-fetches and updates data", async () => {
    const firstData = { value: 1 };
    const secondData = { value: 2 };
    const fetcher = vi.fn()
      .mockResolvedValueOnce(firstData)
      .mockResolvedValueOnce(secondData);

    const { result } = renderHook(() => usePageData(fetcher));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(firstData);

    void result.current.refresh();

    await waitFor(() => expect(result.current.data).toEqual(secondData));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
