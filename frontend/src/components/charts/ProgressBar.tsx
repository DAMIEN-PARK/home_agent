interface Segment {
  label: string;
  value: number;
  colorClassName: string;
}

interface ProgressBarProps {
  segments: Segment[];
  height?: number;
}

export function ProgressBar({ segments, height = 16 }: ProgressBarProps) {
  const total = segments.reduce((a, s) => a + s.value, 0);
  if (total === 0) {
    return <div className="text-xs text-stone-400">할일 없음</div>;
  }
  return (
    <div
      className="flex w-full rounded overflow-hidden"
      style={{ height }}
      role="img"
      aria-label="progress"
    >
      {segments.map((s, i) => {
        const pct = (s.value / total) * 100;
        if (pct === 0) return null;
        return (
          <div
            key={i}
            className={s.colorClassName}
            style={{ width: `${pct}%` }}
            title={`${s.label}: ${s.value}`}
          />
        );
      })}
    </div>
  );
}
