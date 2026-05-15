import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, test, vi } from "vitest";

import Calendar from "@/pages/Calendar";

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderCalendar() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <Calendar />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test("renders events from API", async () => {
  const now = new Date();
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      events: [
        {
          id: "e1",
          title: "Standup",
          source: "google",
          start_at: new Date(now.getFullYear(), now.getMonth(), 15, 10).toISOString(),
          end_at: null,
          description: null,
        },
        {
          id: "e2",
          title: "회의",
          source: "local",
          start_at: new Date(now.getFullYear(), now.getMonth(), 15, 15).toISOString(),
          end_at: null,
          description: null,
        },
      ],
    }),
  });

  renderCalendar();
  await waitFor(() => expect(screen.getByText("Standup")).toBeInTheDocument());
  expect(screen.getByText("회의")).toBeInTheDocument();
});
