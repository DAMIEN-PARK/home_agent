import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, test, vi } from "vitest";

import Schedule from "@/pages/Schedule";

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderSchedule() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <Schedule />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test("renders domain chat region with schedule border + agent tag + textarea", () => {
  const { container } = renderSchedule();
  const borderRegion = container.querySelector(
    ".border-l-4.border-domain-schedule",
  );
  expect(borderRegion).toBeTruthy();
  expect(borderRegion!.textContent).toMatch(/schedule_agent/);
  expect(borderRegion!.querySelector("textarea")).toBeTruthy();
  expect(container.querySelector(".bg-domain-schedule-soft")).toBeTruthy();
});

test("sends domain message and renders assistant reply", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      assistant_message: "다음 주 화요일 14:00 가능합니다.",
      tool_calls: [],
    }),
  });

  renderSchedule();
  const textarea = screen.getByPlaceholderText(/이 도메인에만 묻기/);
  await userEvent.type(textarea, "다음 주 일정 알려줘");
  await userEvent.click(screen.getByRole("button", { name: "전송" }));

  await waitFor(() =>
    expect(
      screen.getByText("다음 주 화요일 14:00 가능합니다."),
    ).toBeInTheDocument(),
  );

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/chat/schedule",
    expect.objectContaining({ method: "POST" }),
  );
});
