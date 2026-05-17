import { useState } from "react";

import { getDeviceId, setDeviceName } from "@/lib/device";

interface Props {
  onSaved: (name: string) => void;
}

export function DeviceSetup({ onSaved }: Props) {
  const [name, setName] = useState("");
  const deviceId = getDeviceId();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setDeviceName(trimmed);
    onSaved(trimmed);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white rounded-lg shadow p-6 space-y-4"
      >
        <div>
          <h1 className="text-lg font-semibold text-stone-800">
            이 기기 이름을 정해주세요
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            예: 데스크탑, 노트북-거실, 와이프-맥북
          </p>
        </div>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="기기 이름"
          className="w-full border border-stone-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={!name.trim()}
          className="w-full bg-indigo-600 text-white py-2 rounded disabled:opacity-40"
        >
          시작
        </button>
        <p className="text-xs text-stone-400 font-mono break-all">
          device_id: {deviceId}
        </p>
      </form>
    </div>
  );
}
