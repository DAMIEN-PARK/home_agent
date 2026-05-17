import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { postDomainChat } from "@/lib/api";

interface Turn {
  who: "user" | "assistant";
  text: string;
}

const TEMP_USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

export default function Schedule() {
  const [thread, setThread] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const send = useMutation({
    mutationFn: (msg: string) => postDomainChat("schedule", msg, TEMP_USER_ID),
    onSuccess: (data) =>
      setThread((t) => [...t, { who: "assistant", text: data.assistant_message }]),
  });

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    setThread((t) => [...t, { who: "user", text: draft }]);
    send.mutate(draft);
    setDraft("");
  };

  return (
    <div className="p-6">
      <h1 className="text-xl mb-4 text-domain-schedule">일정 도메인 챗</h1>
      <section className="border-l-4 border-domain-schedule bg-white p-4 rounded">
        <div className="mb-3">
          <span className="inline-block px-2 py-0.5 text-xs rounded bg-domain-schedule-soft text-domain-schedule">
            schedule_agent
          </span>
          <span className="ml-2 text-sm">도메인 챗</span>
          <p className="text-xs text-stone-500 mt-1">
            scope: schedule.* · calendar MCP only
          </p>
        </div>
        <div className="space-y-2 mb-3 min-h-[120px]">
          {thread.map((t, i) => (
            <div
              key={i}
              className={t.who === "user" ? "text-indigo-600" : "text-stone-800"}
            >
              <span className="font-mono text-xs text-stone-400 mr-2">{t.who}</span>
              {t.text}
            </div>
          ))}
          {send.isPending && (
            <div className="text-stone-400 text-sm">생각 중…</div>
          )}
        </div>
        <form onSubmit={onSubmit} className="flex gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="이 도메인에만 묻기 — 일정·비전·목표"
            className="flex-1 border rounded px-3 py-2 text-sm"
            rows={2}
          />
          <button
            type="submit"
            className="px-4 bg-domain-schedule text-white rounded text-sm"
          >
            전송
          </button>
        </form>
      </section>
    </div>
  );
}
