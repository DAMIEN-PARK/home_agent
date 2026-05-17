import { useQuery } from "@tanstack/react-query";

import { getEvents, type EventDto } from "@/lib/api";

const TEMP_USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

function monthRange(now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return { from: start.toISOString(), to: end.toISOString() };
}

export default function Calendar() {
  const { from, to } = monthRange();
  const { data, isLoading } = useQuery({
    queryKey: ["events", from, to],
    queryFn: () => getEvents(TEMP_USER_ID, from, to),
  });

  const byDay = new Map<string, EventDto[]>();
  for (const e of data?.events ?? []) {
    const day = e.start_at.slice(0, 10);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push(e);
  }

  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const cells: (Date | null)[] = [];
  for (let i = 0; i < firstDay.getDay(); i++) cells.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++)
    cells.push(new Date(now.getFullYear(), now.getMonth(), d));

  return (
    <div className="p-6">
      <h1 className="text-xl mb-4 text-domain-schedule">
        {now.getFullYear()}년 {now.getMonth() + 1}월
      </h1>
      {isLoading && <div>로딩…</div>}
      <div className="grid grid-cols-7 border border-stone-200">
        {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
          <div key={d} className="bg-stone-50 px-2 py-1 text-xs uppercase">
            {d}
          </div>
        ))}
        {cells.map((cell, i) => {
          const key = cell ? cell.toISOString().slice(0, 10) : `empty-${i}`;
          const events = (cell && byDay.get(key)) || [];
          return (
            <div
              key={key}
              className="border-t border-stone-200 min-h-[90px] p-1 text-xs"
            >
              {cell && <div className="text-stone-400">{cell.getDate()}</div>}
              {events.map((e) => (
                <div
                  key={e.id}
                  className={`mt-1 px-1 truncate border-l-2 ${e.source === "google" ? "border-emerald-500" : "border-domain-schedule"}`}
                >
                  {e.title}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
