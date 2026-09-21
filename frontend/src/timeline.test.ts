import { describe, expect, it } from "vitest";
import { HOUR_TICKS, daySegments, weekSegments } from "./timeline";
import type { ScheduleItem } from "./types";

describe("timeline helpers", () => {
  it("positions segments as a percentage of the day", () => {
    const segments = daySegments([
      { from: "06:00:00", to: "12:00:00", data: { temperature: 21 } },
    ]);

    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      startPercent: 25,
      widthPercent: 25,
      index: 0,
      label: "21°",
    });
  });

  it("treats a 24:00 end as the end of the day", () => {
    const segments = daySegments([{ from: "18:00:00", to: "24:00:00" }]);

    expect(segments[0].startPercent).toBe(75);
    expect(segments[0].widthPercent).toBe(25);
    expect(segments[0].startPercent + segments[0].widthPercent).toBe(100);
  });

  it("sorts blocks and keeps the index stable for click mapping", () => {
    const segments = daySegments([
      { from: "20:00:00", to: "22:00:00" },
      { from: "07:00:00", to: "09:00:00" },
    ]);

    expect(segments.map((segment) => segment.from)).toEqual([
      "07:00:00",
      "20:00:00",
    ]);
    expect(segments.map((segment) => segment.index)).toEqual([0, 1]);
  });

  it("builds segments for every day of the week", () => {
    const schedule: ScheduleItem = {
      id: "living_room",
      name: "Living room",
      monday: [{ from: "07:00:00", to: "09:00:00" }],
    };

    const week = weekSegments(schedule);
    expect(week.monday).toHaveLength(1);
    expect(week.tuesday).toEqual([]);
    expect(week.sunday).toEqual([]);
  });

  it("exposes hour ticks for the axis", () => {
    expect(HOUR_TICKS).toEqual([0, 6, 12, 18, 24]);
  });
});
