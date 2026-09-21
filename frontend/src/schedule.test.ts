import { describe, expect, it } from "vitest";
import {
  DAY_GROUPS,
  blocksFromLegacy,
  buildUpdateMessage,
  copyDayTo,
  copyDayToBlocks,
  describeBlock,
  draftToTimeRange,
  emptyDraft,
  findBlockIndex,
  sameBlock,
  timeRangeToDraft,
  todayDay,
  toStorageTime,
  validateDraft,
  withDayBlocks,
} from "./schedule";
import type { ScheduleItem } from "./types";

describe("block identity", () => {
  it("matches a block by value, not by position", () => {
    const blocks = [
      { from: "06:00:00", to: "08:00:00" },
      { from: "09:00:00", to: "11:00:00", data: { temperature: 21 } },
    ];
    expect(findBlockIndex(blocks, { from: "09:00:00", to: "11:00:00", data: { temperature: 21 } })).toBe(1);
    // The same range with different data is a different block.
    expect(findBlockIndex(blocks, { from: "09:00:00", to: "11:00:00", data: { temperature: 22 } })).toBe(-1);
    expect(findBlockIndex(blocks, undefined)).toBe(-1);
  });

  it("re-finds an edited block after another day's edit reorders the list", () => {
    const original = { from: "09:00:00", to: "11:00:00", data: { temperature: 21 } };
    const draft = timeRangeToDraft(original, 1);
    expect(draft.origin).toEqual(original);

    // Someone else inserted an earlier block, shifting every index down.
    const reloaded = [
      { from: "05:00:00", to: "06:00:00" },
      { from: "06:00:00", to: "08:00:00" },
      { from: "09:00:00", to: "11:00:00", data: { temperature: 21 } },
    ];
    expect(findBlockIndex(reloaded, draft.origin)).toBe(2);
    expect(draft.index).toBe(1);
  });

  it("ignores key order when comparing block data", () => {
    expect(
      sameBlock(
        { from: "09:00:00", to: "11:00:00", data: { temperature: 21, fan_mode: "low" } },
        { from: "09:00:00", to: "11:00:00", data: { fan_mode: "low", temperature: 21 } },
      ),
    ).toBe(true);
  });

  it("reports a block that no longer exists", () => {
    const blocks = [{ from: "06:00:00", to: "08:00:00" }];
    const draft = timeRangeToDraft({ from: "09:00:00", to: "11:00:00" }, 0);
    expect(findBlockIndex(blocks, draft.origin)).toBe(-1);
  });
});

describe("schedule helpers", () => {
  it("maps a JavaScript day index to a schedule day", () => {
    expect(todayDay(new Date("2026-08-03T12:00:00Z"))).toBe("monday");
    expect(todayDay(new Date("2026-08-09T12:00:00Z"))).toBe("sunday");
  });

  it("stores a midnight end time as the end of the day", () => {
    expect(toStorageTime("00:00", true)).toBe("24:00:00");
    expect(toStorageTime("22:00", true)).toBe("22:00:00");
    expect(toStorageTime("07:30")).toBe("07:30:00");
  });

  it("omits empty block data", () => {
    expect(draftToTimeRange({ ...emptyDraft(), from: "07:00", to: "09:00" })).toEqual({
      from: "07:00:00",
      to: "09:00:00",
    });
  });

  it("keeps only the configured block values", () => {
    const range = draftToTimeRange({
      ...emptyDraft(),
      hvac_mode: "heat",
      temperature: "21.5",
      humidity: "45",
    });

    expect(range.data).toEqual({
      hvac_mode: "heat",
      temperature: 21.5,
      humidity: 45,
    });
  });

  it("round-trips a stored block into a draft", () => {
    const draft = timeRangeToDraft(
      { from: "22:00:00", to: "24:00:00", data: { temperature: 18 } },
      2,
    );

    expect(draft).toMatchObject({
      index: 2,
      from: "22:00",
      to: "00:00",
      temperature: "18",
    });
  });

  it("rejects invalid and overlapping blocks", () => {
    const blocks = [{ from: "07:00:00", to: "09:00:00" }];

    expect(
      validateDraft({ ...emptyDraft(), from: "09:00", to: "08:00" }, blocks),
    ).toContain("after the start time");
    expect(
      validateDraft({ ...emptyDraft(), from: "08:00", to: "10:00" }, blocks),
    ).toContain("overlaps");
    expect(
      validateDraft({ ...emptyDraft(), from: "09:00", to: "10:00" }, blocks),
    ).toBeNull();
  });

  it("rejects a partial temperature range", () => {
    expect(
      validateDraft(
        { ...emptyDraft(), from: "07:00", to: "09:00", target_temp_low: "18" },
        [],
      ),
    ).toContain("low and a high");
  });

  it("rejects mixing a target temperature with a range", () => {
    expect(
      validateDraft(
        {
          ...emptyDraft(),
          from: "07:00",
          to: "09:00",
          temperature: "21",
          target_temp_low: "18",
          target_temp_high: "24",
        },
        [],
      ),
    ).toContain("either");
  });

  it("always sends every day in an update message", () => {
    const schedule: ScheduleItem = {
      id: "living_room",
      name: "Living room",
      friday: [{ from: "09:00:00", to: "10:00:00" }],
    };

    const message = buildUpdateMessage(
      withDayBlocks(schedule, "monday", [
        { from: "09:00:00", to: "10:00:00" },
        { from: "07:00:00", to: "08:00:00" },
      ]),
    );

    expect(message).toMatchObject({
      type: "schedule/update",
      schedule_id: "living_room",
      name: "Living room",
      monday: [
        { from: "07:00:00", to: "08:00:00" },
        { from: "09:00:00", to: "10:00:00" },
      ],
      friday: [{ from: "09:00:00", to: "10:00:00" }],
      tuesday: [],
      sunday: [],
    });
  });

  it("describes a block for the card summary", () => {
    expect(describeBlock({ from: "07:00:00", to: "09:00:00" })).toBe("No changes");
    expect(
      describeBlock({
        from: "07:00:00",
        to: "09:00:00",
        data: { hvac_mode: "heat_cool", temperature: 21 },
      }),
    ).toBe("heat cool · 21°");
  });

  it("converts legacy daily times into one block", () => {
    expect(blocksFromLegacy({ on_time: "06:30:00", off_time: "22:00:00" })).toEqual([
      { from: "06:30:00", to: "22:00:00" },
    ]);
    expect(blocksFromLegacy(null)).toEqual([{ from: "07:00:00", to: "22:00:00" }]);
    expect(blocksFromLegacy({ on_time: "22:00:00", off_time: "06:30:00" })).toEqual([]);
  });

  it("exposes day-group quick picks", () => {
    expect(DAY_GROUPS.all).toHaveLength(7);
    expect(DAY_GROUPS.weekdays).toEqual([
      "monday",
      "tuesday",
      "wednesday",
      "thursday",
      "friday",
    ]);
    expect(DAY_GROUPS.weekend).toEqual(["saturday", "sunday"]);
  });

  it("copies a day to multiple days in replace mode without mutating input", () => {
    const original: ScheduleItem = {
      id: "living_room",
      name: "Living room",
      monday: [{ from: "07:00:00", to: "09:00:00", data: { temperature: 21 } }],
      tuesday: [{ from: "20:00:00", to: "22:00:00" }],
    };
    const snapshot = JSON.parse(JSON.stringify(original));

    const { schedule, conflicts } = copyDayTo(
      original,
      "monday",
      ["tuesday", "wednesday"],
      "replace",
    );

    expect(conflicts).toEqual([]);
    expect(schedule.tuesday).toEqual([
      { from: "07:00:00", to: "09:00:00", data: { temperature: 21 } },
    ]);
    expect(schedule.wednesday).toEqual([
      { from: "07:00:00", to: "09:00:00", data: { temperature: 21 } },
    ]);
    // The copied blocks are independent clones.
    schedule.tuesday![0].data!.temperature = 99;
    expect(schedule.wednesday![0].data!.temperature).toBe(21);
    // The source schedule is untouched.
    expect(original).toEqual(snapshot);
  });

  it("merges non-overlapping blocks and reports conflicting days", () => {
    const schedule: ScheduleItem = {
      id: "living_room",
      name: "Living room",
      monday: [{ from: "07:00:00", to: "09:00:00" }],
      tuesday: [{ from: "20:00:00", to: "22:00:00" }],
      wednesday: [{ from: "08:00:00", to: "10:00:00" }],
    };

    const result = copyDayTo(
      schedule,
      "monday",
      ["tuesday", "wednesday"],
      "merge",
    );

    // Tuesday has no overlap, so the block is added and sorted.
    expect(result.schedule.tuesday).toEqual([
      { from: "07:00:00", to: "09:00:00" },
      { from: "20:00:00", to: "22:00:00" },
    ]);
    // Wednesday's existing block overlaps, so nothing is added and it is a conflict.
    expect(result.schedule.wednesday).toEqual([
      { from: "08:00:00", to: "10:00:00" },
    ]);
    expect(result.conflicts).toEqual(["wednesday"]);
  });

  it("copies blocks from another schedule into target days", () => {
    const destination: ScheduleItem = {
      id: "bedroom",
      name: "Bedroom",
      monday: [{ from: "06:00:00", to: "07:00:00" }],
    };

    const { schedule, conflicts } = copyDayToBlocks(
      [{ from: "18:00:00", to: "20:00:00" }],
      destination,
      ["monday", "sunday"],
      "merge",
    );

    expect(conflicts).toEqual([]);
    expect(schedule.monday).toEqual([
      { from: "06:00:00", to: "07:00:00" },
      { from: "18:00:00", to: "20:00:00" },
    ]);
    expect(schedule.sunday).toEqual([{ from: "18:00:00", to: "20:00:00" }]);
  });
});
