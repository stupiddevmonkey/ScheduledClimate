export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown> & {
    friendly_name?: string;
    current_temperature?: number;
    temperature?: number;
    target_temp_low?: number;
    target_temp_high?: number;
    humidity?: number;
    current_humidity?: number;
    hvac_action?: string;
    hvac_modes?: string[];
    preset_mode?: string;
    preset_modes?: string[];
    fan_mode?: string;
    fan_modes?: string[];
    swing_mode?: string;
    swing_modes?: string[];
    swing_horizontal_mode?: string;
    swing_horizontal_modes?: string[];
    min_temp?: number;
    max_temp?: number;
    target_temp_step?: number;
    min_humidity?: number;
    max_humidity?: number;
    supported_features?: number;
    schedule_enabled?: boolean;
    schedule_entity_id?: string | null;
    schedule_id?: string | null;
    schedule_active?: boolean;
    active_schedule_block?: ScheduleBlockData | null;
    next_schedule_event?: string | null;
    schedule_issues?: string[];
    legacy_schedule?: { on_time: string; off_time: string } | null;
    timer_action?: string | null;
    timer_deadline?: string | null;
    target_key?: string;
    target_name?: string;
    room_entities?: string[];
    plan_options?: string[];
    active_plan?: string | null;
    plan_selection_mode?: "manual" | "outdoor_temp";
    plan_resolved_automatically?: boolean;
    plan_schedules?: Record<string, string | null>;
    override_active?: boolean;
    override_until?: string | null;
    override_block?: ScheduleBlockData | null;
  };
}

export interface ScheduleBlockData {
  hvac_mode?: string | null;
  temperature?: number | null;
  target_temp_low?: number | null;
  target_temp_high?: number | null;
  fan_mode?: string | null;
  humidity?: number | null;
}

export const SCHEDULE_DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

export type ScheduleDay = (typeof SCHEDULE_DAYS)[number];

export interface ScheduleTimeRange {
  from: string;
  to: string;
  data?: Record<string, string | number | boolean>;
}

export type ScheduleItem = {
  id: string;
  name: string;
  icon?: string;
} & Partial<Record<ScheduleDay, ScheduleTimeRange[]>>;

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  user?: { is_admin?: boolean };
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>,
    target?: Record<string, unknown>,
  ): Promise<unknown>;
  callWS<T>(message: Record<string, unknown>): Promise<T>;
  connection?: {
    subscribeMessage<T>(
      callback: (message: T) => void,
      message: Record<string, unknown>,
    ): Promise<() => void>;
  };
}

export interface ScheduledClimateCardConfig {
  type: "custom:scheduled-climate-card";
  entity: string;
  name?: string;
  layout?: "standard" | "compact";
  show_schedule?: boolean;
  show_timer?: boolean;
  show_plan?: boolean;
  show_override?: boolean;
  schedule_editable?: boolean;
  default_schedule_day?: ScheduleDay;
  default_plan?: string;
  timer_presets?: number[];
}

export const DEFAULT_PRESETS = [15, 30, 60, 120];
