interface SparklineProps {
  data: number[];
  strokeClassName?: string;
  height?: number;
  width?: number;
}

export function Sparkline({
  data,
  strokeClassName = "stroke-stone-500",
  height = 32,
  width = 120,
}: SparklineProps) {
  if (data.length === 0) {
    return <div className="text-xs text-stone-400">데이터 없음</div>;
  }
  const max = Math.max(...data, 1);
  const denom = data.length === 1 ? 1 : data.length - 1;
  const points = data
    .map((v, i) => `${(i / denom) * width},${height - (v / max) * height}`)
    .join(" ");
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-label="sparkline"
    >
      <polyline
        points={points}
        fill="none"
        strokeWidth={2}
        className={strokeClassName}
      />
    </svg>
  );
}
