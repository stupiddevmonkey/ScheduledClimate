import { LitElement, css, html, nothing } from "lit";
import type {
  HomeAssistant,
  ScheduleDay,
  ScheduledClimateCardConfig,
} from "./types";
import { DEFAULT_PRESETS, SCHEDULE_DAYS } from "./types";
import { DAY_LABELS } from "./schedule";

export class ScheduledClimateCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  hass?: HomeAssistant;
  private _config?: ScheduledClimateCardConfig;

  setConfig(config: ScheduledClimateCardConfig): void {
    this._config = { ...config };
  }

  private _setValue(key: keyof ScheduledClimateCardConfig, value: unknown): void {
    if (!this._config) return;
    const config = { ...this._config, [key]: value };
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected render() {
    if (!this.hass || !this._config) return nothing;
    const entities = Object.values(this.hass.states).filter(
      (state) =>
        state.entity_id.startsWith("climate.") &&
        "schedule_enabled" in state.attributes,
    );
    const presets = (this._config.timer_presets ?? DEFAULT_PRESETS).join(", ");

    return html`
      <div class="form">
        <label>
          Entity
          <select
            .value=${this._config.entity ?? ""}
            @change=${(event: Event) =>
              this._setValue("entity", (event.target as HTMLSelectElement).value)}
          >
            <option value="" disabled>Select an entity</option>
            ${entities.map(
              (state) => html`
                <option value=${state.entity_id}>
                  ${state.attributes.friendly_name ?? state.entity_id}
                </option>
              `,
            )}
          </select>
        </label>
        <label>
          Card name
          <input
            type="text"
            .value=${this._config.name ?? ""}
            @input=${(event: Event) =>
              this._setValue("name", (event.target as HTMLInputElement).value)}
          />
        </label>
        <label>
          Layout
          <select
            name="layout"
            .value=${this._config.layout ?? "standard"}
            @change=${(event: Event) =>
              this._setValue(
                "layout",
                (event.target as HTMLSelectElement).value,
              )}
          >
            <option value="standard">Standard</option>
            <option value="compact">Compact</option>
          </select>
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_schedule !== false}
            @change=${(event: Event) =>
              this._setValue(
                "show_schedule",
                (event.target as HTMLInputElement).checked,
              )}
          />
          Show schedule controls
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.schedule_editable !== false}
            @change=${(event: Event) =>
              this._setValue(
                "schedule_editable",
                (event.target as HTMLInputElement).checked,
              )}
          />
          Allow editing the schedule
        </label>
        <label>
          Day shown first
          <select
            name="default_schedule_day"
            .value=${this._config.default_schedule_day ?? ""}
            @change=${(event: Event) =>
              this._setValue(
                "default_schedule_day",
                ((event.target as HTMLSelectElement).value as ScheduleDay) ||
                  undefined,
              )}
          >
            <option value="">Today</option>
            ${SCHEDULE_DAYS.map(
              (day) => html`<option value=${day}>${DAY_LABELS[day]}</option>`,
            )}
          </select>
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_timer !== false}
            @change=${(event: Event) =>
              this._setValue(
                "show_timer",
                (event.target as HTMLInputElement).checked,
              )}
          />
          Show timer controls
        </label>
        <label>
          Timer presets (minutes)
          <input
            type="text"
            .value=${presets}
            @change=${(event: Event) => {
              const values = (event.target as HTMLInputElement).value
                .split(",")
                .map((value) => Number.parseInt(value.trim(), 10))
                .filter((value) => Number.isFinite(value) && value > 0);
              this._setValue("timer_presets", values.length ? values : DEFAULT_PRESETS);
            }}
          />
        </label>
      </div>
    `;
  }

  static styles = css`
    :host { display: block; }
    .form { display: grid; gap: 16px; padding: 8px 0; }
    label { display: grid; gap: 6px; color: var(--primary-text-color); }
    .toggle { display: flex; align-items: center; gap: 10px; }
    input[type="checkbox"] { accent-color: var(--primary-color); }
    select, input[type="text"] {
      box-sizing: border-box;
      width: 100%;
      min-height: 42px;
      padding: 8px 10px;
      color: var(--primary-text-color);
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      font: inherit;
    }
  `;
}

if (!customElements.get("scheduled-climate-card-editor")) {
  customElements.define("scheduled-climate-card-editor", ScheduledClimateCardEditor);
}
