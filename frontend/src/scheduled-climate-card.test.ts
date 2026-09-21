import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ScheduledClimateCard } from "./scheduled-climate-card";
import { ScheduledClimateCardEditor } from "./scheduled-climate-card-editor";
import { ScheduledClimateScheduleDialog } from "./scheduled-climate-schedule-dialog";
import { ScheduledClimateOverrideDialog } from "./scheduled-climate-override-dialog";
import type {
  HassEntity,
  HomeAssistant,
  ScheduleItem,
  ScheduledClimateCardConfig,
} from "./types";

const ENTITY_ID = "climate.living_room_scheduled";
const SECOND_ID = "climate.living_room_fan_scheduled";
const SCHEDULE_ID = "living_room";

function schedule(): ScheduleItem {
  return {
    id: SCHEDULE_ID,
    name: "Living room",
    monday: [{ from: "07:00:00", to: "09:00:00", data: { temperature: 21 } }],
  };
}

function state(attributes: HassEntity["attributes"] = {}): HassEntity {
  return {
    entity_id: ENTITY_ID,
    state: "heat_cool",
    attributes: {
      friendly_name: "Living room",
      current_temperature: 21,
      target_temp_low: 19,
      target_temp_high: 23,
      min_temp: 7,
      max_temp: 35,
      target_temp_step: 0.5,
      supported_features: 1,
      hvac_modes: ["off", "heat_cool"],
      swing_horizontal_mode: "off",
      swing_horizontal_modes: ["off", "on"],
      schedule_enabled: true,
      schedule_entity_id: "schedule.living_room",
      schedule_id: SCHEDULE_ID,
      schedule_active: true,
      next_schedule_event: null,
      timer_action: null,
      timer_deadline: null,
      ...attributes,
    },
  };
}

async function renderCard(
  entityState = state(),
  callService = vi.fn().mockResolvedValue(undefined),
  callWS = vi.fn().mockResolvedValue([schedule()]),
  isAdmin = true,
): Promise<{
  card: ScheduledClimateCard;
  callService: ReturnType<typeof vi.fn>;
  callWS: ReturnType<typeof vi.fn>;
}> {
  const card = new ScheduledClimateCard();
  card.setConfig({
    type: "custom:scheduled-climate-card",
    entity: ENTITY_ID,
    default_schedule_day: "monday",
    timer_presets: [15, 30],
  });
  card.hass = {
    states: { [ENTITY_ID]: entityState },
    user: { is_admin: isAdmin },
    callService,
    callWS,
  } as unknown as HomeAssistant;
  document.body.append(card);
  await card.updateComplete;
  await card.updateComplete;
  return { card, callService, callWS };
}

function button(root: ParentNode, label: string): HTMLButtonElement {
  const match = [...root.querySelectorAll("button")].find(
    (item) => item.textContent?.trim() === label,
  );
  if (!match) throw new Error(`Button not found: ${label}`);
  return match as HTMLButtonElement;
}

function collapseButton(
  card: ScheduledClimateCard,
  section: string,
): HTMLButtonElement {
  const match = card.shadowRoot!.querySelector<HTMLButtonElement>(
    `button[aria-controls="${section}-controls"]`,
  );
  if (!match) throw new Error(`Collapse button not found: ${section}`);
  return match;
}

function scheduleDialog(
  card: ScheduledClimateCard,
): ScheduledClimateScheduleDialog {
  return card.shadowRoot!.querySelector<ScheduledClimateScheduleDialog>(
    "scheduled-climate-schedule-dialog",
  )!;
}

function overrideDialog(
  card: ScheduledClimateCard,
): ScheduledClimateOverrideDialog {
  return card.shadowRoot!.querySelector<ScheduledClimateOverrideDialog>(
    "scheduled-climate-override-dialog",
  )!;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  document.body.replaceChildren();
  localStorage.clear();
});

describe("scheduled-climate-card", () => {
  it("renders native-style range and horizontal swing controls", async () => {
    const { card, callService } = await renderCard();
    const range = card.shadowRoot!.querySelector<HTMLElement>(".range-target")!;
    const controls = range.querySelectorAll<HTMLElement>(".number-control");
    const decreaseLow = range.querySelector<HTMLButtonElement>(
      'button[aria-label="Decrease low"]',
    )!;
    const horizontalSwing = [...card.shadowRoot!.querySelectorAll("label")].find(
      (label) => label.textContent?.includes("Horizontal swing"),
    )!.querySelector("select")!;

    expect(card.shadowRoot!.querySelector(".thermostat")).not.toBeNull();
    expect(controls).toHaveLength(2);
    expect(horizontalSwing.value).toBe("off");

    decreaseLow.click();
    await vi.waitFor(() =>
      expect(callService).toHaveBeenCalledWith("climate", "set_temperature", {
        entity_id: ENTITY_ID,
        target_temp_low: 18.5,
        target_temp_high: 23,
      }),
    );
  });

  it("renders compact mode without a dial", async () => {
    const card = new ScheduledClimateCard();
    card.setConfig({
      type: "custom:scheduled-climate-card",
      entity: ENTITY_ID,
      layout: "compact",
    });
    card.hass = {
      states: { [ENTITY_ID]: state() },
      user: { is_admin: true },
      callService: vi.fn().mockResolvedValue(undefined),
      callWS: vi.fn().mockResolvedValue([schedule()]),
    } as unknown as HomeAssistant;
    document.body.append(card);
    await card.updateComplete;

    expect(card.shadowRoot!.querySelector("ha-card")?.classList).toContain(
      "compact",
    );
    expect(card.shadowRoot!.querySelector(".thermostat")).toBeNull();
    expect(card.shadowRoot!.querySelector(".compact-status")?.textContent).toContain(
      "21°",
    );
  });

  it("selects compact mode in the visual editor", async () => {
    const editor = new ScheduledClimateCardEditor();
    const config: ScheduledClimateCardConfig = {
      type: "custom:scheduled-climate-card",
      entity: ENTITY_ID,
    };
    editor.setConfig(config);
    editor.hass = {
      states: { [ENTITY_ID]: state() },
      callService: vi.fn(),
      callWS: vi.fn(),
    } as unknown as HomeAssistant;
    const listener = vi.fn();
    editor.addEventListener("config-changed", listener);
    document.body.append(editor);
    await editor.updateComplete;

    const layout = editor.shadowRoot!.querySelector<HTMLSelectElement>(
      'select[name="layout"]',
    )!;
    expect(layout.value).toBe("standard");
    layout.value = "compact";
    layout.dispatchEvent(new Event("change"));

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail.config.layout).toBe(
      "compact",
    );
  });

  it("opens native more information for the selected entity", async () => {
    const { card } = await renderCard();
    const listener = vi.fn();
    card.addEventListener("hass-more-info", listener);

    card.shadowRoot!
      .querySelector<HTMLButtonElement>('button[aria-label="More information"]')!
      .click();

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      entityId: ENTITY_ID,
    });
  });

  it("persists independent collapse state for each entity", async () => {
    const { card } = await renderCard(
      state({ preset_mode: "home", preset_modes: ["home", "away"] }),
    );

    for (const section of ["preset", "timer"]) {
      collapseButton(card, section).click();
      await card.updateComplete;
      expect(collapseButton(card, section).getAttribute("aria-expanded")).toBe(
        "false",
      );
      expect(
        card.shadowRoot!.querySelector<HTMLElement>(`#${section}-controls`)!.hidden,
      ).toBe(true);
    }

    card.remove();
    const restored = await renderCard(
      state({ preset_mode: "home", preset_modes: ["home", "away"] }),
    );
    for (const section of ["preset", "timer"]) {
      expect(collapseButton(restored.card, section).getAttribute("aria-expanded")).toBe(
        "false",
      );
    }
  });

  it("starts a timer from the compact timer row", async () => {
    const { card, callService } = await renderCard();

    button(card.shadowRoot!, "Off later").click();
    await vi.waitFor(() =>
      expect(callService).toHaveBeenCalledWith(
        "scheduled_climate",
        "start_off_timer",
        { entity_id: ENTITY_ID, duration: { seconds: 1800 } },
      ),
    );
  });

  it("renders target chips only when the room has more than one entity", async () => {
    const single = await renderCard();
    expect(single.card.shadowRoot!.querySelector(".target-chips")).toBeNull();
    single.card.remove();

    const secondState: HassEntity = {
      ...state(),
      entity_id: SECOND_ID,
      attributes: { ...state().attributes, friendly_name: "Living room fan" },
    };
    const roomState = state({ room_entities: [ENTITY_ID, SECOND_ID] });
    const card = new ScheduledClimateCard();
    card.setConfig({ type: "custom:scheduled-climate-card", entity: ENTITY_ID });
    card.hass = {
      states: {
        [ENTITY_ID]: roomState,
        [SECOND_ID]: {
          ...secondState,
          attributes: {
            ...secondState.attributes,
            room_entities: [ENTITY_ID, SECOND_ID],
          },
        },
      },
      user: { is_admin: true },
      callService: vi.fn().mockResolvedValue(undefined),
      callWS: vi.fn().mockResolvedValue([schedule()]),
    } as unknown as HomeAssistant;
    document.body.append(card);
    await card.updateComplete;

    const chips = card.shadowRoot!.querySelector(".target-chips");
    expect(chips).not.toBeNull();
    expect(chips!.textContent).toContain("Living room");
    expect(chips!.textContent).toContain("Living room fan");
  });

  it("selects a plan from the plan chip", async () => {
    const { card, callService } = await renderCard(
      state({
        plan_options: ["Comfort", "Eco"],
        active_plan: "Comfort",
        plan_selection_mode: "outdoor_temp",
        plan_resolved_automatically: false,
        plan_schedules: { Comfort: SCHEDULE_ID, Eco: null },
      }),
    );

    const chip = card.shadowRoot!.querySelector<HTMLButtonElement>(".chip")!;
    expect(chip.textContent).toContain("Comfort");
    chip.click();
    await card.updateComplete;

    button(card.shadowRoot!, "Eco").click();
    await vi.waitFor(() =>
      expect(callService).toHaveBeenCalledWith(
        "scheduled_climate",
        "select_plan",
        { entity_id: ENTITY_ID, plan: "Eco" },
      ),
    );
  });

  it("offers Automatic only when the plan mode is not manual", async () => {
    const { card } = await renderCard(
      state({
        plan_options: ["Comfort"],
        active_plan: "Comfort",
        plan_selection_mode: "manual",
        plan_schedules: { Comfort: SCHEDULE_ID },
      }),
    );
    card.shadowRoot!.querySelector<HTMLButtonElement>(".chip")!.click();
    await card.updateComplete;
    expect(() => button(card.shadowRoot!, "Automatic")).toThrow();
  });

  it("holds the temperature through the override dialog", async () => {
    const { card, callService } = await renderCard(state({ temperature: 21 }));

    button(card.shadowRoot!, "Hold").click();
    await card.updateComplete;
    const dialog = overrideDialog(card);
    await dialog.updateComplete;

    button(dialog.shadowRoot!, "Hold").click();
    await vi.waitFor(() =>
      expect(callService).toHaveBeenCalledWith("scheduled_climate", "set_override", {
        entity_id: ENTITY_ID,
        until_next_block: true,
        temperature: 21,
      }),
    );
  });

  it("edits a schedule block through the dialog and writes a full week", async () => {
    const callWS = vi.fn().mockResolvedValue([schedule()]);
    const { card } = await renderCard(
      state({
        plan_options: ["Comfort"],
        active_plan: "Comfort",
        plan_schedules: { Comfort: SCHEDULE_ID },
      }),
      undefined,
      callWS,
    );

    button(card.shadowRoot!, "Edit schedule").click();
    await card.updateComplete;
    const dialog = scheduleDialog(card);
    await dialog.updateComplete;
    await vi.waitFor(() =>
      expect(callWS).toHaveBeenCalledWith({ type: "schedule/list" }),
    );
    await dialog.updateComplete;

    button(dialog.shadowRoot!, "Mon").click();
    await dialog.updateComplete;
    button(dialog.shadowRoot!, "Add block").click();
    await dialog.updateComplete;

    const times = dialog.shadowRoot!.querySelectorAll<HTMLInputElement>(
      '.draft input[type="time"]',
    );
    times[0].value = "18:00";
    times[0].dispatchEvent(new Event("input"));
    times[1].value = "21:00";
    times[1].dispatchEvent(new Event("input"));
    await dialog.updateComplete;

    button(dialog.shadowRoot!, "Save block").click();
    await vi.waitFor(() => {
      const update = callWS.mock.calls.find(
        (call) => (call[0] as Record<string, unknown>).type === "schedule/update",
      );
      expect(update).toBeDefined();
    });

    const message = callWS.mock.calls.find(
      (call) => (call[0] as Record<string, unknown>).type === "schedule/update",
    )![0] as Record<string, unknown>;
    expect(message.schedule_id).toBe(SCHEDULE_ID);
    expect(message.monday).toEqual([
      { from: "07:00:00", to: "09:00:00", data: { temperature: 21 } },
      { from: "18:00:00", to: "21:00:00" },
    ]);
    expect(message.sunday).toEqual([]);
  });

  it("shows a read-only schedule to non-administrators and never mutates", async () => {
    const callWS = vi.fn().mockResolvedValue([schedule()]);
    const { card } = await renderCard(
      state({
        plan_options: ["Comfort"],
        active_plan: "Comfort",
        plan_schedules: { Comfort: SCHEDULE_ID },
      }),
      undefined,
      callWS,
      false,
    );

    // The Hold button is available to non-admins.
    expect(() => button(card.shadowRoot!, "Hold")).not.toThrow();

    button(card.shadowRoot!, "Edit schedule").click();
    await card.updateComplete;
    const dialog = scheduleDialog(card);
    await dialog.updateComplete;
    await vi.waitFor(() =>
      expect(callWS).toHaveBeenCalledWith({ type: "schedule/list" }),
    );
    await dialog.updateComplete;

    expect(dialog.shadowRoot!.querySelector(".timeline")).not.toBeNull();
    expect(dialog.shadowRoot!.querySelector(".block-list")?.textContent).toContain(
      "07:00 – 09:00",
    );
    expect(() => button(dialog.shadowRoot!, "Add block")).toThrow();

    // No mutating websocket command was ever issued.
    for (const call of callWS.mock.calls) {
      const type = (call[0] as Record<string, unknown>).type;
      expect(type).toBe("schedule/list");
    }
  });

  it("shows service failures and unavailable state", async () => {
    const errorCall = vi.fn().mockRejectedValue(new Error("Service unavailable"));
    const { card } = await renderCard(state(), errorCall);

    button(card.shadowRoot!, "off").click();
    await vi.waitFor(() =>
      expect(card.shadowRoot!.querySelector('[role="status"]')?.textContent).toBe(
        "Service unavailable",
      ),
    );

    card.hass = {
      states: { [ENTITY_ID]: { ...state(), state: "unavailable" } },
      user: { is_admin: true },
      callService: errorCall,
      callWS: vi.fn().mockResolvedValue([schedule()]),
    } as unknown as HomeAssistant;
    await card.updateComplete;

    expect(card.shadowRoot!.textContent).toContain("The climate entity is unavailable.");
    expect(card.shadowRoot!.querySelector('[aria-label="Climate controls"]')).toBeNull();
  });
});
