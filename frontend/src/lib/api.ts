// Uses the Vite dev-server `/api/*` proxy (vite.config.ts rewrites to backend :8000).
import { getDeviceId, getDeviceName } from "@/lib/device";

export interface EventDto {
  id: string;
  title: string;
  source: string;
  start_at: string;
  end_at: string | null;
  description: string | null;
}

function deviceHeaders(): Record<string, string> {
  const h: Record<string, string> = { "X-Device-Id": getDeviceId() };
  const name = getDeviceName();
  if (name) h["X-Device-Name"] = name;
  return h;
}

export async function postChat(message: string, userId: string) {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...deviceHeaders() },
    body: JSON.stringify({ message, user_id: userId }),
  });
  if (!r.ok) throw new Error(`chat failed: ${r.status}`);
  return r.json() as Promise<{
    assistant_message: string;
    tool_calls: unknown[];
  }>;
}

export async function getEvents(userId: string, from: string, to: string) {
  const q = new URLSearchParams({ user_id: userId, from, to });
  const r = await fetch(`/api/events?${q.toString()}`, {
    headers: deviceHeaders(),
  });
  if (!r.ok) throw new Error(`events failed: ${r.status}`);
  return r.json() as Promise<{ events: EventDto[] }>;
}
