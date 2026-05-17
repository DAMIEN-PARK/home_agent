import { useQuery } from "@tanstack/react-query";

import { Sparkline } from "@/components/charts/Sparkline";
import { ProgressBar } from "@/components/charts/ProgressBar";
import { getEvents, getTasks } from "@/lib/api";

const TEMP_USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

function monthlyEventCounts(events: { start_at: string }[]): number[] {
  const now = new Date();
  // Last 6 months including current — index 0 = oldest
  const months: number[] = new Array(6).fill(0);
  for (const e of events) {
    const d = new Date(e.start_at);
    const monthsAgo =
      (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
    if (monthsAgo >= 0 && monthsAgo < 6) {
      months[5 - monthsAgo]++;
    }
  }
  return months;
}

export default function Dashboard() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth() - 5, 1).toISOString();
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString();

  const { data: eventsData = { events: [] } } = useQuery({
    queryKey: ["events", from, to],
    queryFn: () => getEvents(TEMP_USER_ID, from, to),
  });
  const { data: tasks = [] } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => getTasks(),
  });

  const sparkData = monthlyEventCounts(eventsData.events);
  const segments = [
    {
      label: "open",
      value: tasks.filter((t) => t.status === "open").length,
      colorClassName: "bg-domain-todo",
    },
    {
      label: "done",
      value: tasks.filter((t) => t.status === "done").length,
      colorClassName: "bg-emerald-500",
    },
    {
      label: "deferred",
      value: tasks.filter((t) => t.status === "deferred").length,
      colorClassName: "bg-stone-400",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl">대시보드</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <section className="bg-white p-4 rounded border border-stone-200">
          <h2 className="text-sm text-stone-500 mb-2">최근 6개월 일정 분포</h2>
          <Sparkline
            data={sparkData}
            strokeClassName="stroke-domain-schedule"
            height={48}
            width={240}
          />
        </section>
        <section className="bg-white p-4 rounded border border-stone-200">
          <h2 className="text-sm text-stone-500 mb-2">할 일 상태 분포</h2>
          <ProgressBar segments={segments} />
          <div className="mt-2 text-xs text-stone-500 flex gap-3">
            {segments.map((s) => (
              <span key={s.label}>
                {s.label}: {s.value}
              </span>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
