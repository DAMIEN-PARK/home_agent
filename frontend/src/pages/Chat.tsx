import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { postChat } from "@/lib/api";

interface Turn {
  who: "user" | "assistant";
  text: string;
}

const TEMP_USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

export default function Chat() {
  const [thread, setThread] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const send = useMutation({
    mutationFn: (msg: string) => postChat(msg, TEMP_USER_ID),
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
    <div className="h-screen flex flex-col">
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {thread.map((t, i) => (
          <div
            key={i}
            className={t.who === "user" ? "text-indigo-600" : "text-stone-800"}
          >
            <span className="font-mono text-xs text-stone-400 mr-2">{t.who}</span>
            {t.text}
          </div>
        ))}
        {send.isPending && <div className="text-stone-400">생각 중…</div>}
      </div>
      <form
        onSubmit={onSubmit}
        className="border-t border-stone-200 p-3 flex gap-2 bg-white"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="메시지를 입력하세요…"
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          type="submit"
          className="bg-indigo-600 text-white px-4 rounded"
        >
          전송
        </button>
      </form>
    </div>
  );
}
