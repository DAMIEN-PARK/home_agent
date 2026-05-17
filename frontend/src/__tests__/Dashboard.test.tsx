import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, test, vi } from "vitest";

import Dashboard from "@/pages/Dashboard";

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Dashboard />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test("renders Sparkline + ProgressBar with mocked events and tasks", async () => {
  // /api/events response
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      events: [
        {
          id: "e1",
          title: "회의",
          source: "local",
          start_at: new Date().toISOString(),
          end_at: null,
          description: null,
        },
      ],
    }),
  });
  // /api/todo/tasks response — returns array directly (matches backend list[TaskOut])
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => [
      {
        id: "t1",
        title: "장보기",
        status: "open",
        priority: 3,
        due_at: null,
        completed_at: null,
      },
      {
        id: "t2",
        title: "운동",
        status: "done",
        priority: 3,
        due_at: null,
        completed_at: new Date().toISOString(),
      },
    ],
  });

  const { container } = renderDashboard();

  await waitFor(() => expect(screen.getByText("대시보드")).toBeInTheDocument());
  // Wait for the queries to settle and chart components to render
  await waitFor(() => {
    expect(container.querySelector("polyline")).toBeTruthy();
  });
  expect(container.querySelector('[role="img"]')).toBeTruthy();
  expect(screen.getByText(/최근 6개월 일정 분포/)).toBeInTheDocument();
  expect(screen.getByText(/할 일 상태 분포/)).toBeInTheDocument();
});
