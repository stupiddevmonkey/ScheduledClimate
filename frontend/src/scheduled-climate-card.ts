import { LitElement, css, html, nothing } from "lit";
import "./scheduled-climate-card-editor";
import type {
  HassEntity,
  HomeAssistant,
  ScheduleDay,
  ScheduleItem,
  ScheduleTimeRange,
  ScheduledClimateCardConfig,
} from "./types";
import { DEFAULT_PRESETS, SCHEDULE_DAYS } from "./types";
import type { BlockDraft } from "./schedule";
import {
  DAY_LABELS,
  blocksFromLegacy,
  buildUpdateMessage,
  describeBlock,
  draftToTimeRange,
  emptyDraft,
  shortTime,
  sortBlocks,
  timeRangeToDraft,
  todayDay,
  validateDraft,
  withDayBlocks,
} from "./schedule";

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

const UNAVAILABLE = new Set(["unavailable", "unknown"]);
const COLLAPSE_STORAGE_KEY = "scheduled-climate-card:collapsed";
type CollapsibleSection = "preset" | "schedule" | "timer";
type CollapseState = Record<CollapsibleSection, boolean>;

export class ScheduledClimateCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _busy: { state: true },
    _message: { state: true },
    _timerMinutes: { state: true },
    _collapsed: { state: true },
    _schedule: { state: true },
    _selectedDay: { state: true },
    _draft: { state: true },
    _scheduleError: { state: true },
  };

  hass?: HomeAssistant;
  private _config?: ScheduledClimateCardConfig;
  private _busy = false;
  private _message = "";
  private _timerMinutes = 30;
  private _schedule?: ScheduleItem;
  private _selectedDay: ScheduleDay = todayDay();
  private _draft?: BlockDraft;
  private _scheduleError = "";
  private _loadedScheduleId = "";
  private _unsubscribeSchedules?: () => void;
  private _collapsed: CollapseState = {
    preset: false,
    schedule: false,
    timer: false,
  };

  static getConfigElement(): HTMLElement {
    return document.createElement("scheduled-climate-card-editor");
  }

  static getStubConfig(): ScheduledClimateCardConfig {
    return {
      type: "custom:scheduled-climate-card",
      entity: "",
      layout: "standard",
      show_schedule: true,
      show_timer: true,
      schedule_editable: true,
      timer_presets: DEFAULT_PRESETS,
    };
  }

  setConfig(config: ScheduledClimateCardConfig): void {
    if (!config.entity) throw new Error("Scheduled Climate Card requires an entity");
    this._config = {
      layout: "standard",
      show_schedule: true,
      show_timer: true,
      schedule_editable: true,
      timer_presets: DEFAULT_PRESETS,
      ...config,
    };
    this._selectedDay = this._config.default_schedule_day ?? todayDay();
    this._collapsed = this._loadCollapseState(config.entity);
  }

  getCardSize(): number {
    return 7;
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribeSchedules?.();
    this._unsubscribeSchedules = undefined;
    this._loadedScheduleId = "";
  }

  protected willUpdate(): void {
    const scheduleId = this._state?.attributes.schedule_id ?? "";
    if (scheduleId !== this._loadedScheduleId) {
      this._loadedScheduleId = scheduleId;
      this._schedule = undefined;
      this._draft = undefined;
      if (scheduleId) void this._subscribeSchedules();
    }
  }

  private get _isAdmin(): boolean {
    return this.hass?.user?.is_admin === true;
  }

  private get _canEditSchedule(): boolean {
    return this._isAdmin && this._config?.schedule_editable !== false;
  }

  private async _subscribeSchedules(): Promise<void> {
    this._unsubscribeSchedules?.();
    this._unsubscribeSchedules = undefined;
    await this._loadSchedules();
    if (!this.hass?.connection) return;
    try {
      this._unsubscribeSchedules = await this.hass.connection.subscribeMessage(
        () => void this._loadSchedules(),
        { type: "schedule/subscribe" },
      );
    } catch {
      // Live updates are optional; the card still reloads after its own edits.
    }
  }

  private async _loadSchedules(): Promise<void> {
    const scheduleId = this._state?.attributes.schedule_id;
    if (!this.hass || !scheduleId) return;
    try {
      const items = await this.hass.callWS<ScheduleItem[]>({
        type: "schedule/list",
      });
      this._schedule = items.find((item) => item.id === scheduleId);
    } catch (error) {
      this._scheduleError =
        error instanceof Error ? error.message : "Unable to load the schedule";
    }
  }

  private get _state(): HassEntity | undefined {
    return this._config && this.hass?.states[this._config.entity];
  }

  private _storageKey(entityId: string): string {
    return `${COLLAPSE_STORAGE_KEY}:${entityId}`;
  }

  private _loadCollapseState(entityId: string): CollapseState {
    const defaults: CollapseState = {
      preset: false,
      schedule: false,
      timer: false,
    };
    try {
      const stored = localStorage.getItem(this._storageKey(entityId));
      if (!stored) return defaults;
      const value = JSON.parse(stored) as Partial<CollapseState>;
      return {
        preset: value.preset === true,
        schedule: value.schedule === true,
        timer: value.timer === true,
      };
    } catch {
      return defaults;
    }
  }

  private _toggleSection(section: CollapsibleSection): void {
    if (!this._config) return;
    this._collapsed = {
      ...this._collapsed,
      [section]: !this._collapsed[section],
    };
    try {
      localStorage.setItem(
        this._storageKey(this._config.entity),
        JSON.stringify(this._collapsed),
      );
    } catch {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }

  private _renderCollapseButton(
    section: CollapsibleSection,
    label: string,
    controls: string,
  ) {
    const expanded = !this._collapsed[section];
    return html`
      <button
        class="collapse-button icon"
        title=${`${expanded ? "Collapse" : "Expand"} ${label.toLowerCase()}`}
        aria-label=${`${expanded ? "Collapse" : "Expand"} ${label.toLowerCase()}`}
        aria-expanded=${expanded}
        aria-controls=${controls}
        @click=${() => this._toggleSection(section)}
      >
        <ha-icon icon=${expanded ? "mdi:chevron-up" : "mdi:chevron-down"}></ha-icon>
      </button>
    `;
  }

  private async _call(
    domain: string,
    service: string,
    data: Record<string, unknown> = {},
  ): Promise<boolean> {
    if (!this.hass || !this._config || this._busy) return false;
    this._busy = true;
    this._message = "";
    try {
      await this.hass.callService(domain, service, {
        entity_id: this._config.entity,
        ...data,
      });
      this._message = "Saved";
      return true;
    } catch (error) {
      this._message = error instanceof Error ? error.message : "Command failed";
      return false;
    } finally {
      this._busy = false;
    }
  }

  private _formatValue(value: unknown, suffix = ""): string {
    return typeof value === "number" ? `${value}${suffix}` : "--";
  }

  private _modeIcon(mode: string): string {
    return {
      off: "mdi:power",
      heat: "mdi:fire",
      cool: "mdi:snowflake",
      heat_cool: "mdi:autorenew",
      auto: "mdi:calendar-sync",
      dry: "mdi:water-percent",
      fan_only: "mdi:fan",
    }[mode] ?? "mdi:thermostat";
  }

  private _adjustTemperature(field: string, value: number, step: number): void {
    const state = this._state;
    if (!state) return;
    const attrs = state.attributes;
    const data: Record<string, unknown> = {
      [field]: Math.round((value + step) * 100) / 100,
    };
    if (field === "target_temp_low") data.target_temp_high = attrs.target_temp_high;
    if (field === "target_temp_high") data.target_temp_low = attrs.target_temp_low;
    void this._call("climate", "set_temperature", data);
  }

  private _renderTemperatureControl(
    label: string,
    field: string,
    value: number,
    unit: string,
    step: number,
    min: number,
    max: number,
  ) {
    return html`
      <div class="number-control" aria-label=${label}>
        <button
          class="step-button"
          title=${`Decrease ${label.toLowerCase()}`}
          aria-label=${`Decrease ${label.toLowerCase()}`}
          ?disabled=${this._busy || value - step < min}
          @click=${() => this._adjustTemperature(field, value, -step)}
        ><ha-icon icon="mdi:minus"></ha-icon></button>
        <div class="target-value">
          <span>${value}</span><small>${unit}</small>
          <label>${label}</label>
        </div>
        <button
          class="step-button"
          title=${`Increase ${label.toLowerCase()}`}
          aria-label=${`Increase ${label.toLowerCase()}`}
          ?disabled=${this._busy || value + step > max}
          @click=${() => this._adjustTemperature(field, value, step)}
        ><ha-icon icon="mdi:plus"></ha-icon></button>
      </div>
    `;
  }

  private _renderSelect(
    label: string,
    value: string | undefined,
    values: string[] | undefined,
    service: string,
    field: string,
  ) {
    if (!values?.length) return nothing;
    return html`
      <label class="field">
        <span>${label}</span>
        <select
          .value=${value ?? ""}
          ?disabled=${this._busy}
          @change=${(event: Event) =>
            this._call("climate", service, {
              [field]: (event.target as HTMLSelectElement).value,
            })}
        >
          ${values.map((item) => html`<option value=${item}>${item.replaceAll("_", " ")}</option>`)}
        </select>
      </label>
    `;
  }

  private _renderClimate(state: HassEntity) {
    const attrs = state.attributes;
    const unit = String(attrs.unit_of_measurement ?? "°");
    const modes = attrs.hvac_modes ?? [];
    const target = attrs.temperature;
    const targetLow = attrs.target_temp_low;
    const targetHigh = attrs.target_temp_high;
    const step = attrs.target_temp_step ?? 0.5;
    const compact = this._config?.layout === "compact";

    return html`
      <section class="climate" aria-label="Climate controls">
        ${compact
          ? html`<div class="compact-status">
              <div>
                <span class="current-label">Current</span>
                <span class="compact-current">${this._formatValue(attrs.current_temperature, unit)}</span>
              </div>
              ${attrs.hvac_action
                ? html`<span class="action"><span class="pulse"></span>${attrs.hvac_action.replaceAll("_", " ")}</span>`
                : nothing}
            </div>`
          : html`<div class=${`thermostat ${state.state === "off" ? "is-off" : "is-active"}`}>
              <div class="dial-ring">
                <div class="dial-content">
                  <span class="current-label">Current</span>
                  <span class="current">${this._formatValue(attrs.current_temperature, unit)}</span>
                  ${attrs.hvac_action
                    ? html`<span class="action"><span class="pulse"></span>${attrs.hvac_action.replaceAll("_", " ")}</span>`
                    : nothing}
                </div>
              </div>
            </div>`}
        ${typeof target === "number"
          ? this._renderTemperatureControl(
              "Target",
              "temperature",
              target,
              unit,
              step,
              attrs.min_temp ?? 7,
              attrs.max_temp ?? 35,
            )
          : typeof targetLow === "number" && typeof targetHigh === "number"
            ? html`<div class="range-target" aria-label="Target temperature range">
                ${this._renderTemperatureControl(
                  "Low",
                  "target_temp_low",
                  targetLow,
                  unit,
                  step,
                  attrs.min_temp ?? 7,
                  targetHigh,
                )}
                ${this._renderTemperatureControl(
                  "High",
                  "target_temp_high",
                  targetHigh,
                  unit,
                  step,
                  targetLow,
                  attrs.max_temp ?? 35,
                )}
              </div>`
            : nothing}
        <div class="modes feature-buttons" role="group" aria-label="HVAC mode">
          ${modes.map(
            (mode) => html`
              <button
                class=${state.state === mode ? "selected" : ""}
                ?disabled=${this._busy}
                aria-pressed=${state.state === mode}
                @click=${() => this._call("climate", "set_hvac_mode", { hvac_mode: mode })}
              ><ha-icon icon=${this._modeIcon(mode)}></ha-icon><span>${mode.replaceAll("_", " ")}</span></button>
            `,
          )}
        </div>
        <div class="subsection-heading">
          <div><h3>Preset & options</h3><p>${attrs.preset_mode?.replaceAll("_", " ") ?? "Climate settings"}</p></div>
          ${this._renderCollapseButton("preset", "Preset and options", "preset-controls")}
        </div>
        <div id="preset-controls" class="control-grid" ?hidden=${this._collapsed.preset}>
              ${this._renderSelect("Preset", attrs.preset_mode, attrs.preset_modes, "set_preset_mode", "preset_mode")}
              ${this._renderSelect("Fan", attrs.fan_mode, attrs.fan_modes, "set_fan_mode", "fan_mode")}
              ${this._renderSelect("Swing", attrs.swing_mode, attrs.swing_modes, "set_swing_mode", "swing_mode")}
              ${this._renderSelect(
                "Horizontal swing",
                attrs.swing_horizontal_mode,
                attrs.swing_horizontal_modes,
                "set_swing_horizontal_mode",
                "swing_horizontal_mode",
              )}
              ${typeof attrs.humidity === "number"
                ? html`
                    <label class="field">
                      <span>Humidity</span>
                      <input
                        type="number"
                        .value=${String(attrs.humidity)}
                        min=${attrs.min_humidity ?? 30}
                        max=${attrs.max_humidity ?? 99}
                        ?disabled=${this._busy}
                        @change=${(event: Event) =>
                          this._call("climate", "set_humidity", {
                            humidity: Number((event.target as HTMLInputElement).value),
                          })}
                      />
                    </label>
                  `
                : nothing}
          </div>
      </section>
    `;
  }

  private _renderSchedule(state: HassEntity) {
    const nextEvent = state.attributes.next_schedule_event;
    const scheduleId = state.attributes.schedule_id;
    const scheduleEnabled = state.attributes.schedule_enabled;
    const caption = !scheduleId
      ? "No schedule linked"
      : nextEvent
        ? `Next change · ${new Date(nextEvent).toLocaleString()}`
        : scheduleEnabled
          ? "No upcoming change"
          : "Schedule paused";

    return html`
      <section aria-labelledby="schedule-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:calendar-clock"></ha-icon>
          <div class="section-copy">
            <h3 id="schedule-heading">Schedule</h3>
            <p>${caption}</p>
          </div>
          ${scheduleId
            ? html`<button
                class="icon"
                title=${scheduleEnabled ? "Pause schedule" : "Resume schedule"}
                aria-label=${scheduleEnabled ? "Pause schedule" : "Resume schedule"}
                ?disabled=${this._busy}
                @click=${() =>
                  this._call(
                    "scheduled_climate",
                    scheduleEnabled ? "disable_schedule" : "enable_schedule",
                  )}
              >
                <ha-icon
                  icon=${scheduleEnabled ? "mdi:pause" : "mdi:play"}
                ></ha-icon>
              </button>`
            : nothing}
          ${this._renderCollapseButton("schedule", "Schedule", "schedule-controls")}
        </div>
        <div id="schedule-controls" class="collapsible-body" ?hidden=${this._collapsed.schedule}>
          ${scheduleId ? this._renderScheduleEditor(state) : this._renderScheduleLink(state)}
          ${this._scheduleError ? html`<p class="error" role="alert">${this._scheduleError}</p>` : nothing}
        </div>
      </section>
    `;
  }

  private _renderScheduleLink(state: HassEntity) {
    const legacy = state.attributes.legacy_schedule;
    if (!this._canEditSchedule) {
      return html`<p class="caption">Link a schedule helper from the integration options to control this entity on a weekly plan.</p>`;
    }
    return html`
      <p class="caption">
        ${legacy
          ? `Your old daily times (${shortTime(legacy.on_time)} – ${shortTime(legacy.off_time)}) can be converted into a weekly schedule.`
          : "Create a schedule helper to control this entity on a weekly plan."}
      </p>
      <div class="timer-actions">
        <button class="primary" ?disabled=${this._busy} @click=${() => this._createSchedule()}>
          <ha-icon icon="mdi:calendar-plus"></ha-icon>Create schedule
        </button>
      </div>
    `;
  }

  private _renderScheduleEditor(state: HassEntity) {
    if (!this._schedule) {
      return html`<p class="caption">Loading the linked schedule…</p>`;
    }
    const blocks = sortBlocks(this._schedule[this._selectedDay] ?? []);
    return html`
      <div class="day-chips" role="tablist" aria-label="Days of the week">
        ${SCHEDULE_DAYS.map(
          (day) => html`
            <button
              role="tab"
              aria-selected=${day === this._selectedDay}
              class=${day === this._selectedDay ? "selected" : ""}
              @click=${() => this._selectDay(day)}
            >
              ${DAY_LABELS[day]}
            </button>
          `,
        )}
      </div>
      <ul class="block-list">
        ${blocks.length === 0
          ? html`<li class="caption">No blocks on ${DAY_LABELS[this._selectedDay]}</li>`
          : blocks.map(
              (block, index) => html`
                <li class="block">
                  <div class="block-copy">
                    <span>${shortTime(block.from)} – ${shortTime(block.to)}</span>
                    <small>${describeBlock(block)}</small>
                  </div>
                  ${this._canEditSchedule
                    ? html`
                        <button class="icon" title="Edit block" aria-label="Edit block" @click=${() => (this._draft = timeRangeToDraft(block, index))}>
                          <ha-icon icon="mdi:pencil-outline"></ha-icon>
                        </button>
                        <button class="icon" title="Duplicate block" aria-label="Duplicate block" @click=${() => this._duplicateBlock(index)}>
                          <ha-icon icon="mdi:content-duplicate"></ha-icon>
                        </button>
                        <button class="icon" title="Delete block" aria-label="Delete block" @click=${() => this._deleteBlock(index)}>
                          <ha-icon icon="mdi:delete-outline"></ha-icon>
                        </button>
                      `
                    : nothing}
                </li>
              `,
            )}
      </ul>
      ${this._canEditSchedule
        ? html`
            <div class="timer-actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => (this._draft = emptyDraft())}>
                <ha-icon icon="mdi:plus"></ha-icon>Add block
              </button>
              <label class="custom-time">
                <span>Copy to</span>
                <select
                  ?disabled=${this._busy}
                  .value=${""}
                  @change=${(event: Event) => this._copyDay(event.target as HTMLSelectElement)}
                >
                  <option value="">Select a day</option>
                  ${SCHEDULE_DAYS.filter((day) => day !== this._selectedDay).map(
                    (day) => html`<option value=${day}>${DAY_LABELS[day]}</option>`,
                  )}
                </select>
              </label>
            </div>
            ${this._draft ? this._renderDraft(state, this._draft) : nothing}
          `
        : html`<p class="caption">Only administrators can change this schedule.</p>`}
    `;
  }

  private _renderDraft(state: HassEntity, draft: BlockDraft) {
    const attrs = state.attributes;
    const features = attrs.supported_features ?? 0;
    const update = (patch: Partial<BlockDraft>): void => {
      this._draft = { ...(this._draft ?? draft), ...patch };
    };
    const text = (event: Event): string => (event.target as HTMLInputElement).value;

    return html`
      <div class="schedule-grid">
        <label class="field"><span>From</span><input type="time" .value=${draft.from} @input=${(event: Event) => update({ from: text(event) })} /></label>
        <label class="field"><span>To</span><input type="time" .value=${draft.to} @input=${(event: Event) => update({ to: text(event) })} /></label>
        <label class="field">
          <span>Mode</span>
          <select .value=${draft.hvac_mode} @change=${(event: Event) => update({ hvac_mode: text(event) })}>
            <option value="">Unchanged</option>
            ${(attrs.hvac_modes ?? []).map(
              (mode) => html`<option value=${mode} ?selected=${mode === draft.hvac_mode}>${mode.replaceAll("_", " ")}</option>`,
            )}
          </select>
        </label>
        ${features & 8 && (attrs.fan_modes ?? []).length > 0
          ? html`
              <label class="field">
                <span>Fan</span>
                <select .value=${draft.fan_mode} @change=${(event: Event) => update({ fan_mode: text(event) })}>
                  <option value="">Unchanged</option>
                  ${(attrs.fan_modes ?? []).map(
                    (mode) => html`<option value=${mode} ?selected=${mode === draft.fan_mode}>${mode}</option>`,
                  )}
                </select>
              </label>
            `
          : nothing}
        ${features & 1
          ? html`<label class="field"><span>Temperature</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.temperature} @input=${(event: Event) => update({ temperature: text(event) })} /></label>`
          : nothing}
        ${features & 2
          ? html`
              <label class="field"><span>Low</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.target_temp_low} @input=${(event: Event) => update({ target_temp_low: text(event) })} /></label>
              <label class="field"><span>High</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.target_temp_high} @input=${(event: Event) => update({ target_temp_high: text(event) })} /></label>
            `
          : nothing}
        ${features & 4
          ? html`<label class="field"><span>Humidity</span><input type="number" min=${attrs.min_humidity ?? 30} max=${attrs.max_humidity ?? 99} step="1" .value=${draft.humidity} @input=${(event: Event) => update({ humidity: text(event) })} /></label>`
          : nothing}
        <div class="timer-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._saveDraft()}><ha-icon icon="mdi:content-save-outline"></ha-icon>Save block</button>
          <button ?disabled=${this._busy} @click=${() => (this._draft = undefined)}>Cancel</button>
        </div>
      </div>
    `;
  }

  private _selectDay(day: ScheduleDay): void {
    this._selectedDay = day;
    this._draft = undefined;
    this._scheduleError = "";
  }

  private _dayBlocks(): ScheduleTimeRange[] {
    return sortBlocks(this._schedule?.[this._selectedDay] ?? []);
  }

  private async _saveDraft(): Promise<void> {
    const draft = this._draft;
    if (!this._schedule || !draft) return;

    const blocks = this._dayBlocks();
    const error = validateDraft(draft, blocks);
    if (error) {
      this._scheduleError = error;
      return;
    }

    const next = [...blocks];
    if (draft.index === null) next.push(draftToTimeRange(draft));
    else next[draft.index] = draftToTimeRange(draft);

    if (await this._writeSchedule(withDayBlocks(this._schedule, this._selectedDay, next))) {
      this._draft = undefined;
    }
  }

  private async _duplicateBlock(index: number): Promise<void> {
    if (!this._schedule) return;
    const blocks = this._dayBlocks();
    const source = blocks[index];
    if (!source) return;
    this._draft = { ...timeRangeToDraft(source, index), index: null };
    this._scheduleError = "";
  }

  private async _deleteBlock(index: number): Promise<void> {
    if (!this._schedule) return;
    const next = this._dayBlocks().filter((_, position) => position !== index);
    this._draft = undefined;
    await this._writeSchedule(withDayBlocks(this._schedule, this._selectedDay, next));
  }

  private async _copyDay(select: HTMLSelectElement): Promise<void> {
    const target = select.value as ScheduleDay | "";
    select.value = "";
    if (!this._schedule || !target) return;
    await this._writeSchedule(
      withDayBlocks(this._schedule, target, this._dayBlocks()),
    );
  }

  private async _writeSchedule(next: ScheduleItem): Promise<boolean> {
    if (!this.hass || this._busy) return false;
    this._busy = true;
    this._scheduleError = "";
    this._message = "";
    try {
      await this.hass.callWS(buildUpdateMessage(next));
      this._schedule = next;
      this._message = "Saved";
      return true;
    } catch (error) {
      this._scheduleError =
        error instanceof Error ? error.message : "Unable to save the schedule";
      return false;
    } finally {
      this._busy = false;
    }
  }

  private async _createSchedule(): Promise<void> {
    const state = this._state;
    if (!this.hass || !state || this._busy) return;

    const blocks = blocksFromLegacy(state.attributes.legacy_schedule);
    const message: Record<string, unknown> = {
      type: "schedule/create",
      name: this._config?.name ?? state.attributes.friendly_name ?? "Scheduled Climate",
    };
    for (const day of SCHEDULE_DAYS) message[day] = blocks;

    this._busy = true;
    this._scheduleError = "";
    let created: ScheduleItem | undefined;
    try {
      created = await this.hass.callWS<ScheduleItem>(message);
    } catch (error) {
      this._scheduleError =
        error instanceof Error ? error.message : "Unable to create the schedule";
    } finally {
      this._busy = false;
    }

    if (created) {
      await this._call("scheduled_climate", "link_schedule", {
        schedule_id: created.id,
      });
    }
  }

  private _renderTimer(state: HassEntity) {
    const action = state.attributes.timer_action;
    const deadline = state.attributes.timer_deadline;
    const presets = this._config?.timer_presets ?? DEFAULT_PRESETS;
    return html`
      <section aria-labelledby="timer-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:timer-outline"></ha-icon>
          <div class="section-copy"><h3 id="timer-heading">Timer</h3><p>${action && deadline ? `${action} at ${new Date(deadline).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "No active timer"}</p></div>
          ${action ? html`<button class="icon" title="Cancel timer" aria-label="Cancel timer" @click=${() => this._call("scheduled_climate", "cancel_timer")}><ha-icon icon="mdi:timer-off-outline"></ha-icon></button>` : nothing}
          ${this._renderCollapseButton("timer", "Timer", "timer-controls")}
        </div>
        <div id="timer-controls" class="collapsible-body" ?hidden=${this._collapsed.timer}>
        <div class="presets" aria-label="Timer presets">
          ${presets.map((minutes) => html`<button class=${this._timerMinutes === minutes ? "selected" : ""} @click=${() => (this._timerMinutes = minutes)}>${minutes < 60 ? `${minutes}m` : `${minutes / 60}h`}</button>`)}
          <label class="custom-time"><span>Minutes</span><input type="number" min="1" step="1" .value=${String(this._timerMinutes)} @input=${(event: Event) => (this._timerMinutes = Math.max(1, Number((event.target as HTMLInputElement).value)))} /></label>
        </div>
        <div class="timer-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._startTimer("on")}><ha-icon icon="mdi:power"></ha-icon>Turn on later</button>
          <button ?disabled=${this._busy} @click=${() => this._startTimer("off")}><ha-icon icon="mdi:power-off"></ha-icon>Turn off later</button>
        </div>
        </div>
      </section>
    `;
  }

  private _startTimer(action: "on" | "off"): void {
    const seconds = Math.round(this._timerMinutes * 60);
    void this._call("scheduled_climate", `start_${action}_timer`, {
      duration: { seconds },
    });
  }

  protected render() {
    if (!this._config || !this.hass) return nothing;
    const state = this._state;
    if (!state) return html`<ha-card><div class="empty">Entity not found</div></ha-card>`;
    const unavailable = UNAVAILABLE.has(state.state);
    const title = this._config.name ?? state.attributes.friendly_name ?? "Scheduled Climate";

    return html`
      <ha-card class=${`state-${state.state} ${this._config.layout === "compact" ? "compact" : "standard"}`}>
        <header>
          <div class="title-block"><h2>${title}</h2><p>${unavailable ? "Unavailable" : state.state.replaceAll("_", " ")}</p></div>
          <button class="more-info icon" title="More information" aria-label="More information" @click=${this._showMoreInfo}>
            <ha-icon icon="mdi:dots-vertical"></ha-icon>
          </button>
        </header>
        ${unavailable ? html`<div class="empty">The climate entity is unavailable.</div>` : this._renderClimate(state)}
        ${!unavailable && this._config.show_schedule !== false ? this._renderSchedule(state) : nothing}
        ${!unavailable && this._config.show_timer !== false ? this._renderTimer(state) : nothing}
        ${this._message ? html`<div class="message" role="status">${this._message}</div>` : nothing}
      </ha-card>
    `;
  }

  private _showMoreInfo(): void {
    if (!this._config) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId: this._config.entity },
    }));
  }

  static styles = css`
    :host { display: block; color: var(--primary-text-color); --feature-color: var(--state-climate-heat-color, var(--primary-color)); }
    ha-card { overflow: hidden; border-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px)); }
    ha-card.state-cool { --feature-color: var(--state-climate-cool-color, #2196f3); }
    ha-card.state-dry { --feature-color: var(--state-climate-dry-color, #f9a825); }
    ha-card.state-fan_only { --feature-color: var(--state-climate-fan_only-color, #8e8e93); }
    ha-card.state-off { --feature-color: var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e)); }
    header, section { padding: 16px 20px; }
    header { position: relative; min-height: 50px; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }
    .title-block { min-width: 0; text-align: center; }
    .title-block p { text-transform: capitalize; }
    .more-info { position: absolute; right: 8px; inset-inline-end: 8px; border: 0; border-radius: var(--ha-border-radius-pill, 999px); color: var(--secondary-text-color); background: transparent; }
    h2, h3, p { margin: 0; letter-spacing: 0; }
    h2 { overflow: hidden; font-size: var(--ha-font-size-l, 18px); line-height: var(--ha-line-height-expanded, 1.4); text-overflow: ellipsis; white-space: nowrap; }
    h3 { font-size: var(--ha-font-size-m, 14px); line-height: 1.4; }
    p, .caption, .field > span, .custom-time > span { color: var(--secondary-text-color); font-size: 12px; }
    section + section { border-top: 1px solid var(--divider-color); }
    .climate { padding-top: 4px; }
    .thermostat { display: grid; place-items: center; padding: 8px 0 14px; }
    .dial-ring { width: min(230px, 68vw); aspect-ratio: 1; display: grid; place-items: center; border: 12px solid color-mix(in srgb, var(--feature-color) 72%, var(--card-background-color)); border-right-color: color-mix(in srgb, var(--feature-color) 16%, var(--card-background-color)); border-radius: 50%; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--feature-color) 18%, transparent); box-sizing: border-box; }
    .is-off .dial-ring { border-color: color-mix(in srgb, var(--secondary-text-color) 22%, var(--card-background-color)); }
    .dial-content { display: grid; justify-items: center; gap: 3px; }
    .current-label { color: var(--secondary-text-color); font-size: 12px; }
    .current { font-size: 48px; line-height: 1.05; font-weight: 400; font-variant-numeric: tabular-nums; }
    .compact-status { display: flex; min-height: 52px; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 10px; }
    .compact-status > div { display: grid; }
    .compact-current { font-size: 30px; line-height: 1.1; font-weight: 400; font-variant-numeric: tabular-nums; }
    .action { display: flex; align-items: center; gap: 6px; color: var(--secondary-text-color); font-size: 12px; text-transform: capitalize; }
    .pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--state-climate-heat-color, var(--primary-color)); }
    .number-control { display: grid; grid-template-columns: 44px minmax(80px, 1fr) 44px; align-items: center; max-width: 260px; margin: 0 auto; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-pill, 999px); overflow: hidden; }
    .target-value { display: grid; grid-template-columns: auto auto; justify-content: center; align-items: start; padding: 5px 8px; text-align: center; }
    .target-value span { font-size: 22px; font-variant-numeric: tabular-nums; }
    .target-value small { padding-top: 2px; font-size: 12px; }
    .target-value label { grid-column: 1 / -1; color: var(--secondary-text-color); font-size: 10px; }
    .range-target { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .range-target .number-control { grid-template-columns: 36px minmax(56px, 1fr) 36px; width: 100%; }
    .modes, .presets { display: flex; gap: 8px; overflow-x: auto; margin-top: 16px; padding-bottom: 2px; scrollbar-width: thin; }
    button { min-height: 40px; padding: 8px 12px; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-pill, 999px); color: var(--primary-text-color); background: var(--card-background-color); font: inherit; cursor: pointer; text-transform: capitalize; white-space: nowrap; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color)); }
    button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
    button.selected, button.primary { color: var(--text-primary-color, white); background: var(--feature-color); border-color: var(--feature-color); }
    button:disabled { opacity: .55; cursor: wait; }
    button ha-icon { --mdc-icon-size: 18px; margin-right: 6px; vertical-align: -4px; }
    .step-button { min-height: 44px; padding: 8px; border: 0; border-radius: 0; color: var(--feature-color); background: transparent; }
    .step-button ha-icon, .icon ha-icon { margin: 0; }
    .feature-buttons button { display: grid; min-width: 64px; justify-items: center; gap: 3px; padding: 7px 12px; font-size: 11px; }
    .feature-buttons button ha-icon { --mdc-icon-size: 20px; margin: 0; }
    .control-grid, .schedule-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; padding: 12px; border-radius: var(--ha-border-radius-lg, 12px); background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color))); }
    .field { display: grid; gap: 5px; }
    .day-chips { display: flex; gap: 6px; overflow-x: auto; margin-top: 12px; padding-bottom: 2px; scrollbar-width: thin; }
    .day-chips button { flex: 1 0 auto; min-width: 48px; padding: 8px 10px; }
    .block-list { display: grid; gap: 8px; margin: 12px 0 0; padding: 0; list-style: none; }
    .block { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-lg, 12px); }
    .block-copy { display: grid; flex: 1 1 auto; min-width: 0; gap: 2px; }
    .block-copy span { font-variant-numeric: tabular-nums; }
    .block-copy small { color: var(--secondary-text-color); font-size: 12px; text-transform: capitalize; }
    .block .icon { min-height: 36px; padding: 6px; }
    .error { margin-top: 12px; color: var(--error-color, #db4437); font-size: 12px; }
    input, select { box-sizing: border-box; min-width: 0; min-height: 40px; padding: 7px 10px; color: var(--primary-text-color); background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); font: inherit; }
    input[type="checkbox"] { accent-color: var(--primary-color); }
    .section-heading { display: flex; align-items: center; gap: 12px; }
    .subsection-heading { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
    .subsection-heading > div { min-width: 0; flex: 1; }
    .subsection-heading p { margin-top: 3px; text-transform: capitalize; }
    .section-icon { --mdc-icon-size: 22px; flex: 0 0 auto; padding: 9px; border-radius: 50%; color: var(--feature-color); background: color-mix(in srgb, var(--feature-color) 12%, var(--card-background-color)); }
    .section-copy { min-width: 0; flex: 1; }
    .section-heading p { margin-top: 3px; }
    .switch { display: flex; align-items: center; gap: 7px; font-size: 13px; }
    .schedule-grid .primary { align-self: end; }
    .icon { width: 40px; padding: 7px; }
    .icon ha-icon { margin: 0; }
    .collapse-button { flex: 0 0 auto; border: 0; color: var(--secondary-text-color); background: transparent; }
    [hidden] { display: none !important; }
    .custom-time { display: flex; align-items: center; gap: 6px; margin-left: auto; }
    .custom-time input { width: 68px; }
    .timer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }
    .message { padding: 10px 20px; border-top: 1px solid var(--divider-color); color: var(--secondary-text-color); font-size: 13px; }
    .empty { padding: 28px 20px; color: var(--secondary-text-color); text-align: center; }
    ha-card.compact header { min-height: 44px; padding-block: 10px; }
    ha-card.compact .climate { padding: 4px 16px 12px; }
    ha-card.compact .modes { margin-top: 12px; }
    ha-card.compact .subsection-heading { margin-top: 12px; }
    ha-card.compact section:not(.climate) { padding: 12px 16px; }
    ha-card.compact .control-grid, ha-card.compact .schedule-grid { margin-top: 10px; }
    ha-card.compact .feature-buttons button { min-height: 44px; }
    @media (max-width: 420px) {
      header, section { padding: 16px; }
      .control-grid, .schedule-grid { grid-template-columns: 1fr; }
      .timer-actions { grid-template-columns: 1fr; }
      .current { font-size: 42px; }
      .custom-time { margin-left: 0; }
      .range-target { grid-template-columns: 1fr; }
      ha-card.compact .range-target { grid-template-columns: 1fr 1fr; }
      .presets { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow-x: visible; }
      .presets > button { min-width: 0; padding-inline: 6px; }
      .custom-time { grid-column: 1 / -1; width: 100%; }
      .custom-time input { flex: 1; width: auto; }
    }
  `;
}

// A second copy of this bundle (stale dashboard resource, cached module) must not
// throw on load, otherwise the surviving registration is lost with it.
if (!customElements.get("scheduled-climate-card")) {
  customElements.define("scheduled-climate-card", ScheduledClimateCard);
}
window.customCards = window.customCards ?? [];
if (!window.customCards.some((card) => card.type === "scheduled-climate-card")) {
  window.customCards.push({
    type: "scheduled-climate-card",
    name: "Scheduled Climate Card",
    description: "Climate controls with daily schedules and one-shot timers.",
    preview: true,
  });
}
