import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ProgressBar } from "@/components/charts/ProgressBar";

test("renders segments proportional to values with color classes", () => {
  const { container } = render(
    <ProgressBar
      segments={[
        { label: "open", value: 2, colorClassName: "bg-domain-todo" },
        { label: "done", value: 8, colorClassName: "bg-emerald-500" },
      ]}
    />,
  );
  const bar = container.querySelector('[role="img"]');
  expect(bar).toBeTruthy();
  const divs = Array.from(bar!.querySelectorAll("div")) as HTMLElement[];
  expect(divs.length).toBe(2);
  expect(divs[0].className).toContain("bg-domain-todo");
  expect(divs[0].style.width).toBe("20%");
  expect(divs[1].className).toContain("bg-emerald-500");
  expect(divs[1].style.width).toBe("80%");
});

test("renders empty state when all segments zero", () => {
  render(
    <ProgressBar
      segments={[
        { label: "open", value: 0, colorClassName: "bg-domain-todo" },
        { label: "done", value: 0, colorClassName: "bg-emerald-500" },
      ]}
    />,
  );
  expect(screen.getByText("할일 없음")).toBeInTheDocument();
});
