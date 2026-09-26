import { LitElement, css, html, nothing } from "lit";
import "./scheduled-climate-card-editor";
import "./scheduled-climate-schedule-dialog";
import "./scheduled-climate-override-dialog";
import type {
  HassEntity,
  HomeAssistant,
  ScheduledClimateCardConfig,
} from "./types";
import { DEFAULT_PRESETS } from "./types";
import { targetLabel } from "./schedule";

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

const UNAVAILABLE = new Set(["unavailable", "unknown"]);
const COLLAPSE_STORAGE_KEY = "scheduled-climate-card:collapsed";
type CollapsibleSection = "preset" | "timer";
type CollapseState = Record<CollapsibleSection, boolean>;

export class ScheduledClimateCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _busy: { state: true },
    _message: { state: true },
    _timerMinutes: { state: true },
    _collapsed: { state: true },
    _selectedTarget: { state: true },
    _planMenuOpen: { state: true },
    _scheduleOpen: { state: true },
    _overrideOpen: { state: true },
  };

  hass?: HomeAssistant;
  private _config?: ScheduledClimateCardConfig;
  private _busy = false;
  private _message = "";
  private _timerMinutes = 30;
  private _selectedTarget = "";
  private _planMenuOpen = false;
  private _scheduleOpen = false;
  private _overrideOpen = false;
  private _collapsed: CollapseState = { preset: false, timer: false };

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
      show_plan: true,
      show_override: true,
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
      show_plan: true,
      show_override: true,
      schedule_editable: true,
      timer_presets: DEFAULT_PRESETS,
      ...config,
    };
    this._selectedTarget = config.entity;
    this._collapsed = this._loadCollapseState(config.entity);
  }

  getCardSize(): number {
    return 5;
  }

  private get _isAdmin(): boolean {
    return this.hass?.user?.is_admin === true;
  }

  private get _state(): HassEntity | undefined {
    return this._config && this.hass?.states[this._config.entity];
  }

  private get _roomEntities(): string[] {
    const room = this._state?.attributes.room_entities;
    if (room && room.length > 0) return room;
    return this._config ? [this._config.entity] : [];
  }

  private get _selectedState(): HassEntity | undefined {
    if (!this.hass || !this._config) return undefined;
    const room = this._roomEntities;
    const id =
      this._selectedTarget && room.includes(this._selectedTarget)
        ? this._selectedTarget
        : this._config.entity;
    return this.hass.states[id];
  }

  private get _selectedId(): string {
    return this._selectedState?.entity_id ?? this._config?.entity ?? "";
  }

  private _storageKey(entityId: string): string {
    return `${COLLAPSE_STORAGE_KEY}:${entityId}`;
  }

  private _loadCollapseState(entityId: string): CollapseState {
    const defaults: CollapseState = { preset: false, timer: false };
    try {
      const stored = localStorage.getItem(this._storageKey(entityId));
      if (!stored) return defaults;
      const value = JSON.parse(stored) as Partial<CollapseState>;
      return { preset: value.preset === true, timer: value.timer === true };
    } catch {
      return defaults;
    }
  }

  private _toggleSection(section: CollapsibleSection): void {
    if (!this._config) return;
    this._collapsed = { ...this._collapsed, [section]: !this._collapsed[section] };
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
    if (!this.hass || this._busy) return false;
    this._busy = true;
    this._message = "";
    try {
      await this.hass.callService(domain, service, {
        entity_id: this._selectedId,
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

  private _formatTime(value: string): string {
    return new Date(value).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
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
    const state = this._selectedState;
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

  private _renderTargetChips() {
    const room = this._roomEntities;
    if (room.length <= 1) return nothing;
    return html`
      <div class="target-chips" role="tablist" aria-label="Room targets">
        ${room.map((entityId) => {
          const state = this.hass?.states[entityId];
          const label = targetLabel(state, entityId);
          const selected = entityId === this._selectedId;
          return html`<button
            role="tab"
            aria-selected=${selected}
            class=${selected ? "selected" : ""}
            @click=${() => this._selectTarget(entityId)}
          >${label}</button>`;
        })}
      </div>
    `;
  }

  private _selectTarget(entityId: string): void {
    this._selectedTarget = entityId;
    this._planMenuOpen = false;
    this._message = "";
  }

  private _renderPlanChip(state: HassEntity) {
    if (this._config?.show_plan === false) return nothing;
    const attrs = state.attributes;
    const plans = attrs.plan_options ?? [];
    if (plans.length === 0) return nothing;
    const active = attrs.active_plan ?? "—";
    const auto = attrs.plan_resolved_automatically === true;
    const allowAutomatic = attrs.plan_selection_mode !== "manual";

    return html`
      <div class="plan-chip">
        <button
          class="chip"
          aria-haspopup="menu"
          aria-expanded=${this._planMenuOpen}
          ?disabled=${this._busy}
          @click=${() => (this._planMenuOpen = !this._planMenuOpen)}
        >
          <ha-icon icon="mdi:calendar-star"></ha-icon>
          <span>${active}</span>
          ${auto ? html`<small class="auto-badge">Auto</small>` : nothing}
          <ha-icon icon="mdi:menu-down"></ha-icon>
        </button>
        ${this._planMenuOpen
          ? html`<ul class="plan-menu" role="menu">
              ${allowAutomatic
                ? html`<li role="menuitem">
                    <button
                      class=${auto ? "selected" : ""}
                      @click=${() => this._selectPlan("automatic")}
                    >Automatic</button>
                  </li>`
                : nothing}
              ${plans.map(
                (plan) => html`<li role="menuitem">
                  <button
                    class=${!auto && plan === attrs.active_plan ? "selected" : ""}
                    @click=${() => this._selectPlan(plan)}
                  >${plan}</button>
                </li>`,
              )}
            </ul>`
          : nothing}
      </div>
    `;
  }

  private _selectPlan(plan: string): void {
    this._planMenuOpen = false;
    void this._call("scheduled_climate", "select_plan", { plan });
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
            ? html`<div class="range-target">
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
    const attrs = state.attributes;
    const overrideActive = attrs.override_active === true;
    const nextEvent = attrs.next_schedule_event;
    const scheduleId = attrs.schedule_id;
    const scheduleEnabled = attrs.schedule_enabled;

    const caption = overrideActive
      ? attrs.override_until
        ? `Holding until ${this._formatTime(attrs.override_until)}`
        : "Holding temperature"
      : !scheduleId
        ? "No schedule linked"
        : nextEvent
          ? `Next change · ${new Date(nextEvent).toLocaleString()}`
          : scheduleEnabled
            ? "No upcoming change"
            : "Schedule paused";

    return html`
      <section class="summary" aria-labelledby="schedule-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon=${overrideActive ? "mdi:gesture-tap-hold" : "mdi:calendar-clock"}></ha-icon>
          <div class="section-copy">
            <h3 id="schedule-heading">Schedule</h3>
            <p>${caption}</p>
          </div>
          ${overrideActive
            ? html`<button
                class="icon"
                title="Resume schedule"
                aria-label="Resume schedule"
                ?disabled=${this._busy}
                @click=${() => this._call("scheduled_climate", "clear_override")}
              ><ha-icon icon="mdi:play"></ha-icon></button>`
            : scheduleId
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
                ><ha-icon icon=${scheduleEnabled ? "mdi:pause" : "mdi:play"}></ha-icon></button>`
              : nothing}
        </div>
        <div class="summary-actions">
          <button @click=${() => (this._scheduleOpen = true)}>
            <ha-icon icon="mdi:calendar-edit"></ha-icon>Edit schedule
          </button>
          ${this._config?.show_override !== false
            ? html`<button ?disabled=${this._busy} @click=${() => (this._overrideOpen = true)}>
                <ha-icon icon="mdi:gesture-tap-hold"></ha-icon>Hold
              </button>`
            : nothing}
        </div>
      </section>
    `;
  }

  private _renderTimer(state: HassEntity) {
    const action = state.attributes.timer_action;
    const deadline = state.attributes.timer_deadline;
    const presets = this._config?.timer_presets ?? DEFAULT_PRESETS;
    return html`
      <section aria-labelledby="timer-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:timer-outline"></ha-icon>
          <div class="section-copy"><h3 id="timer-heading">Timer</h3><p>${action && deadline ? `${action} at ${this._formatTime(deadline)}` : "No active timer"}</p></div>
          ${action ? html`<button class="icon" title="Cancel timer" aria-label="Cancel timer" @click=${() => this._call("scheduled_climate", "cancel_timer")}><ha-icon icon="mdi:timer-off-outline"></ha-icon></button>` : nothing}
          ${this._renderCollapseButton("timer", "Timer", "timer-controls")}
        </div>
        <div id="timer-controls" class="collapsible-body" ?hidden=${this._collapsed.timer}>
          <div class="timer-row">
            <div class="presets" aria-label="Timer presets">
              ${presets.map((minutes) => html`<button class=${this._timerMinutes === minutes ? "selected" : ""} @click=${() => (this._timerMinutes = minutes)}>${minutes < 60 ? `${minutes}m` : `${minutes / 60}h`}</button>`)}
              <label class="custom-time"><span>Minutes</span><input type="number" min="1" step="1" .value=${String(this._timerMinutes)} @input=${(event: Event) => (this._timerMinutes = Math.max(1, Number((event.target as HTMLInputElement).value)))} /></label>
            </div>
            <div class="timer-actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => this._startTimer("on")}><ha-icon icon="mdi:power"></ha-icon>On later</button>
              <button ?disabled=${this._busy} @click=${() => this._startTimer("off")}><ha-icon icon="mdi:power-off"></ha-icon>Off later</button>
            </div>
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
    const selected = this._selectedState ?? state;
    const unavailable = UNAVAILABLE.has(selected.state);
    const title =
      this._config.name ?? state.attributes.friendly_name ?? "Scheduled Climate";
    const initialPlan =
      this._config.default_plan ?? selected.attributes.active_plan ?? undefined;

    return html`
      <ha-card class=${`state-${selected.state} ${this._config.layout === "compact" ? "compact" : "standard"}`}>
        <header>
          <div class="title-block"><h2>${title}</h2><p>${unavailable ? "Unavailable" : selected.state.replaceAll("_", " ")}</p></div>
          <button class="more-info icon" title="More information" aria-label="More information" @click=${this._showMoreInfo}>
            <ha-icon icon="mdi:dots-vertical"></ha-icon>
          </button>
        </header>
        ${this._renderTargetChips()}
        ${unavailable
          ? html`<div class="empty">The climate entity is unavailable.</div>`
          : html`
              ${this._renderClimate(selected)}
              ${this._config.show_plan !== false ? html`<div class="plan-row">${this._renderPlanChip(selected)}</div>` : nothing}
              ${this._config.show_schedule !== false ? this._renderSchedule(selected) : nothing}
              ${this._config.show_timer !== false ? this._renderTimer(selected) : nothing}
            `}
        ${this._message ? html`<div class="message" role="status">${this._message}</div>` : nothing}
      </ha-card>

      <scheduled-climate-schedule-dialog
        .hass=${this.hass}
        .entityId=${this._config.entity}
        .open=${this._scheduleOpen}
        .initialTarget=${this._selectedId}
        .initialPlan=${initialPlan}
        @dialog-closed=${() => (this._scheduleOpen = false)}
      ></scheduled-climate-schedule-dialog>

      <scheduled-climate-override-dialog
        .hass=${this.hass}
        .entityId=${this._selectedId}
        .open=${this._overrideOpen}
        @dialog-closed=${() => (this._overrideOpen = false)}
      ></scheduled-climate-override-dialog>
    `;
  }

  private _showMoreInfo(): void {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId: this._selectedId },
    }));
  }

  static styles = css`
    :host { display: block; color: var(--primary-text-color); --feature-color: var(--state-climate-heat-color, var(--primary-color)); }
    ha-card { overflow: visible; border-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px)); }
    ha-card.state-cool { --feature-color: var(--state-climate-cool-color, #2196f3); }
    ha-card.state-dry { --feature-color: var(--state-climate-dry-color, #f9a825); }
    ha-card.state-fan_only { --feature-color: var(--state-climate-fan_only-color, #8e8e93); }
    ha-card.state-off { --feature-color: var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e)); }
    header, section { padding: 16px 20px; }
    header { position: relative; min-height: 50px; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }
    .title-block { min-width: 0; text-align: center; }
    .title-block p { text-transform: capitalize; }
    .more-info { position: absolute; right: 8px; inset-inline-end: 8px; border: 0; border-radius: var(--ha-border-radius-pill, 999px); color: var(--secondary-text-color); background: transparent; }
    h2, h3, p { margin: 0; }
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
    .control-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; padding: 12px; border-radius: var(--ha-border-radius-lg, 12px); background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color))); }
    .field { display: grid; gap: 5px; }
    .target-chips { display: flex; gap: 6px; overflow-x: auto; padding: 0 20px 4px; scrollbar-width: thin; }
    .target-chips button { flex: 0 0 auto; text-transform: none; }
    .plan-row { padding: 0 20px 12px; }
    .plan-chip { position: relative; display: inline-block; }
    .chip { display: inline-flex; align-items: center; gap: 6px; text-transform: none; }
    .chip .auto-badge { padding: 1px 7px; border-radius: 999px; color: var(--text-primary-color, white); background: var(--feature-color); font-size: 10px; text-transform: uppercase; }
    .chip ha-icon { margin: 0; }
    .plan-menu { position: absolute; z-index: 5; left: 0; top: calc(100% + 4px); min-width: 180px; margin: 0; padding: 6px; list-style: none; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); background: var(--card-background-color); box-shadow: 0 6px 20px rgba(0,0,0,.2); }
    .plan-menu li { display: block; }
    .plan-menu button { width: 100%; justify-content: flex-start; margin: 2px 0; border: 0; border-radius: 6px; text-align: left; text-transform: none; }
    .summary-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .summary-actions button { flex: 1 1 auto; justify-content: center; }
    .block-copy span { font-variant-numeric: tabular-nums; }
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
    .icon { width: 40px; padding: 7px; }
    .icon ha-icon { margin: 0; }
    .collapse-button { flex: 0 0 auto; border: 0; color: var(--secondary-text-color); background: transparent; }
    [hidden] { display: none !important; }
    .custom-time { display: flex; align-items: center; gap: 6px; margin-left: auto; }
    .custom-time input { width: 68px; }
    .timer-row { display: grid; gap: 12px; margin-top: 14px; }
    .timer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .message { padding: 10px 20px; border-top: 1px solid var(--divider-color); color: var(--secondary-text-color); font-size: 13px; }
    .empty { padding: 28px 20px; color: var(--secondary-text-color); text-align: center; }
    ha-card.compact header { min-height: 44px; padding-block: 10px; }
    ha-card.compact .climate { padding: 4px 16px 12px; }
    ha-card.compact .modes { margin-top: 12px; }
    ha-card.compact .subsection-heading { margin-top: 12px; }
    ha-card.compact section:not(.climate) { padding: 12px 16px; }
    ha-card.compact .control-grid { margin-top: 10px; }
    ha-card.compact .feature-buttons button { min-height: 44px; }
    @media (max-width: 420px) {
      header, section { padding: 16px; }
      .control-grid { grid-template-columns: 1fr; }
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
    description: "Climate controls with weekly schedule plans, holds, and one-shot timers.",
    preview: true,
  });
}
