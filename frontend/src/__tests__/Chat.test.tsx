import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, test, vi } from "vitest";

import Chat from "@/pages/Chat";

const fetchMock = vi.fn();
globalThis.fetch = fetchMock as unknown as typeof fetch;

function renderChat() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <Chat />
    </QueryClientProvider>,
  );
}

beforeEach(() => fetchMock.mockReset());

test("sends message and renders assistant reply", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      assistant_message: "회의 잡았어요",
      tool_calls: [],
    }),
  });

  renderChat();
  const input = screen.getByPlaceholderText(/메시지/);
  await userEvent.type(input, "내일 3시 회의 잡아줘");
  await userEvent.click(screen.getByRole("button", { name: /전송/ }));

  await waitFor(() =>
    expect(screen.getByText("회의 잡았어요")).toBeInTheDocument(),
  );
});
