import type { ScheduleDay, ScheduleItem, ScheduleTimeRange } from "./types";
import { SCHEDULE_DAYS } from "./types";
import { describeBlock, sortBlocks, toMinutes } from "./schedule";

const DAY_MINUTES = 24 * 60;

export interface TimelineSegment {
  from: string;
  to: string;
  startPercent: number;
  widthPercent: number;
  index: number;
  label: string;
}

/** Hour marks rendered along the timeline axis. */
export const HOUR_TICKS = [0, 6, 12, 18, 24] as const;

/**
 * Turn a single day's blocks into positioned timeline segments.
 *
 * Percentages are relative to a 24h day. `index` is the position of the block
 * in the sorted list so a click on a segment maps back to the source block.
 */
export function daySegments(blocks: ScheduleTimeRange[]): TimelineSegment[] {
  const sorted = sortBlocks(blocks);
  return sorted.map((block, index) => {
    const start = toMinutes(block.from);
    const end = toMinutes(block.to, true);
    return {
      from: block.from,
      to: block.to,
      startPercent: (start / DAY_MINUTES) * 100,
      widthPercent: (Math.max(0, end - start) / DAY_MINUTES) * 100,
      index,
      label: describeBlock(block),
    };
  });
}

/** Build timeline segments for every day of the week. */
export function weekSegments(
  schedule: ScheduleItem,
): Record<ScheduleDay, TimelineSegment[]> {
  const result = {} as Record<ScheduleDay, TimelineSegment[]>;
  for (const day of SCHEDULE_DAYS) {
    result[day] = daySegments(schedule[day] ?? []);
  }
  return result;
}
