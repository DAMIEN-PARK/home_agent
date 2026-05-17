import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";

import { Sidebar } from "@/components/Sidebar";
import Calendar from "@/pages/Calendar";
import Chat from "@/pages/Chat";
import Dashboard from "@/pages/Dashboard";
import Schedule from "@/pages/Schedule";

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
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/dashboard" element={<Dashboard />} />
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

  test("schedule route shows domain chat region", () => {
    render(harness("/schedule"));
    expect(screen.getByText("schedule_agent")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/이 도메인에만 묻기/),
    ).toBeInTheDocument();
  });

  test("dashboard route shows charts heading", () => {
    render(harness("/dashboard"));
    expect(screen.getByText("대시보드")).toBeInTheDocument();
  });
});
