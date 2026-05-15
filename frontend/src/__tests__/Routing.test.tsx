import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";

import { Sidebar } from "@/components/Sidebar";
import Calendar from "@/pages/Calendar";
import Chat from "@/pages/Chat";

globalThis.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, json: async () => ({ events: [] }) }),
) as unknown as typeof fetch;

function harness(initialPath: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Sidebar />
        <Routes>
          <Route path="/chat" element={<Chat />} />
          <Route path="/calendar" element={<Calendar />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("routing", () => {
  test("chat route shows chat input", () => {
    render(harness("/chat"));
    expect(screen.getByPlaceholderText(/메시지/)).toBeInTheDocument();
  });

  test("calendar route shows month header", () => {
    render(harness("/calendar"));
    expect(screen.getByText(/년 \d+월/)).toBeInTheDocument();
  });
});
