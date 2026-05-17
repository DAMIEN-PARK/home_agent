import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Sparkline } from "@/components/charts/Sparkline";

test("renders polyline for non-empty data with stroke class", () => {
  const { container } = render(
    <Sparkline data={[1, 3, 2, 5]} strokeClassName="stroke-domain-schedule" />,
  );
  const polyline = container.querySelector("polyline");
  expect(polyline).toBeTruthy();
  expect(polyline!.getAttribute("class")).toContain("stroke-domain-schedule");
  // 4 points -> 4 comma-separated coords
  expect(polyline!.getAttribute("points")!.split(" ").length).toBe(4);
});

test("renders empty state placeholder when data is empty", () => {
  const { container } = render(<Sparkline data={[]} />);
  expect(screen.getByText("데이터 없음")).toBeInTheDocument();
  expect(container.querySelector("polyline")).toBeFalsy();
});
