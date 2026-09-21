import { LitElement, css, html, nothing } from "lit";
import type { HassEntity, HomeAssistant } from "./types";
import { parseNumber } from "./schedule";
import { dialogStyles } from "./dialog-styles";

const DURATION_PRESETS = [30, 60, 120, 240];

interface OverrideDraft {
  hvac_mode: string;
  temperature: string;
  target_temp_low: string;
  target_temp_high: string;
  fan_mode: string;
  humidity: string;
}

function emptyOverrideDraft(): OverrideDraft {
  return {
    hvac_mode: "",
    temperature: "",
    target_temp_low: "",
    target_temp_high: "",
    fan_mode: "",
    humidity: "",
  };
}

export class ScheduledClimateOverrideDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    entityId: { attribute: false },
    open: { attribute: false },
    _draft: { state: true },
    _durationMode: { state: true },
    _minutes: { state: true },
    _busy: { state: true },
    _error: { state: true },
  };

  hass?: HomeAssistant;
  entityId?: string;
  open = false;
  private _draft: OverrideDraft = emptyOverrideDraft();
  private _durationMode: "until_next" | "minutes" = "until_next";
  private _minutes = 60;
  private _busy = false;
  private _error = "";
  private _wasOpen = false;

  private get _state(): HassEntity | undefined {
    return this.entityId ? this.hass?.states[this.entityId] : undefined;
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open") && this.open && !this._wasOpen) {
      this._reset();
    }
    this._wasOpen = this.open;
  }

  private _reset(): void {
    const attrs = this._state?.attributes;
    const features = attrs?.supported_features ?? 0;
    const block = attrs?.override_active ? attrs.override_block : null;
    const text = (value: unknown): string =>
      value === undefined || value === null ? "" : String(value);
    this._draft = {
      hvac_mode: text(block?.hvac_mode),
      temperature: features & 1 ? text(block?.temperature ?? attrs?.temperature) : "",
      target_temp_low:
        features & 2 ? text(block?.target_temp_low ?? attrs?.target_temp_low) : "",
      target_temp_high:
        features & 2 ? text(block?.target_temp_high ?? attrs?.target_temp_high) : "",
      fan_mode: features & 8 ? text(block?.fan_mode ?? attrs?.fan_mode) : "",
      humidity: features & 4 ? text(block?.humidity ?? attrs?.humidity) : "",
    };
    this._durationMode = "until_next";
    this._minutes = 60;
    this._error = "";
    this._busy = false;
  }

  private _close(): void {
    this.open = false;
    this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: true, composed: true }),
    );
  }

  private _update(patch: Partial<OverrideDraft>): void {
    this._draft = { ...this._draft, ...patch };
  }

  private async _confirm(): Promise<void> {
    if (!this.hass || !this.entityId || this._busy) return;
    const data: Record<string, unknown> = {};
    if (this._durationMode === "until_next") data.until_next_block = true;
    else data.duration = { seconds: Math.max(1, Math.round(this._minutes * 60)) };

    if (this._draft.hvac_mode) data.hvac_mode = this._draft.hvac_mode;
    if (this._draft.fan_mode) data.fan_mode = this._draft.fan_mode;
    const temperature = parseNumber(this._draft.temperature);
    if (temperature !== undefined) data.temperature = temperature;
    const low = parseNumber(this._draft.target_temp_low);
    const high = parseNumber(this._draft.target_temp_high);
    if (low !== undefined) data.target_temp_low = low;
    if (high !== undefined) data.target_temp_high = high;
    const humidity = parseNumber(this._draft.humidity);
    if (humidity !== undefined) data.humidity = humidity;

    this._busy = true;
    this._error = "";
    try {
      await this.hass.callService("scheduled_climate", "set_override", {
        entity_id: this.entityId,
        ...data,
      });
      this._close();
    } catch (error) {
      this._error = error instanceof Error ? error.message : "Command failed";
    } finally {
      this._busy = false;
    }
  }

  private async _resume(): Promise<void> {
    if (!this.hass || !this.entityId || this._busy) return;
    this._busy = true;
    this._error = "";
    try {
      await this.hass.callService("scheduled_climate", "clear_override", {
        entity_id: this.entityId,
      });
      this._close();
    } catch (error) {
      this._error = error instanceof Error ? error.message : "Command failed";
    } finally {
      this._busy = false;
    }
  }

  protected render() {
    if (!this.open || !this.hass) return nothing;
    const state = this._state;
    if (!state) return nothing;
    const attrs = state.attributes;
    const features = attrs.supported_features ?? 0;
    const draft = this._draft;
    const overrideActive = attrs.override_active === true;
    const num = (event: Event): string => (event.target as HTMLInputElement).value;

    return html`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Hold temperature</h2>
          </div>
          <div class="grid">
            <label class="field">
              <span>Mode</span>
              <select
                .value=${draft.hvac_mode}
                @change=${(event: Event) =>
                  this._update({ hvac_mode: num(event) })}
              >
                <option value="">Unchanged</option>
                ${(attrs.hvac_modes ?? []).map(
                  (mode) => html`<option value=${mode} ?selected=${mode === draft.hvac_mode}>${mode.replaceAll("_", " ")}</option>`,
                )}
              </select>
            </label>
            ${features & 1
              ? html`<label class="field"><span>Temperature</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.temperature} @input=${(event: Event) => this._update({ temperature: num(event) })} /></label>`
              : nothing}
            ${features & 2
              ? html`
                  <label class="field"><span>Low</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.target_temp_low} @input=${(event: Event) => this._update({ target_temp_low: num(event) })} /></label>
                  <label class="field"><span>High</span><input type="number" min=${attrs.min_temp ?? 7} max=${attrs.max_temp ?? 35} step=${attrs.target_temp_step ?? 0.5} .value=${draft.target_temp_high} @input=${(event: Event) => this._update({ target_temp_high: num(event) })} /></label>
                `
              : nothing}
            ${features & 8 && (attrs.fan_modes ?? []).length > 0
              ? html`
                  <label class="field">
                    <span>Fan</span>
                    <select .value=${draft.fan_mode} @change=${(event: Event) => this._update({ fan_mode: num(event) })}>
                      <option value="">Unchanged</option>
                      ${(attrs.fan_modes ?? []).map(
                        (mode) => html`<option value=${mode} ?selected=${mode === draft.fan_mode}>${mode}</option>`,
                      )}
                    </select>
                  </label>
                `
              : nothing}
            ${features & 4
              ? html`<label class="field"><span>Humidity</span><input type="number" min=${attrs.min_humidity ?? 30} max=${attrs.max_humidity ?? 99} step="1" .value=${draft.humidity} @input=${(event: Event) => this._update({ humidity: num(event) })} /></label>`
              : nothing}
          </div>

          <div class="field">
            <span>How long?</span>
            <div class="radios">
              <label>
                <input
                  type="radio"
                  name="override-duration"
                  ?checked=${this._durationMode === "until_next"}
                  @change=${() => (this._durationMode = "until_next")}
                />
                Until the next scheduled change
              </label>
              <label>
                <input
                  type="radio"
                  name="override-duration"
                  ?checked=${this._durationMode === "minutes"}
                  @change=${() => (this._durationMode = "minutes")}
                />
                For a set time
              </label>
            </div>
          </div>

          ${this._durationMode === "minutes"
            ? html`
                <div class="chips">
                  ${DURATION_PRESETS.map(
                    (minutes) => html`<button
                      class=${this._minutes === minutes ? "selected" : ""}
                      @click=${() => (this._minutes = minutes)}
                    >${minutes < 60 ? `${minutes}m` : `${minutes / 60}h`}</button>`,
                  )}
                  <label class="field" style="min-width:100px">
                    <span>Minutes</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      .value=${String(this._minutes)}
                      @input=${(event: Event) =>
                        (this._minutes = Math.max(
                          1,
                          Number((event.target as HTMLInputElement).value),
                        ))}
                    />
                  </label>
                </div>
              `
            : nothing}

          ${this._error ? html`<p class="error" role="alert">${this._error}</p>` : nothing}
        </div>

        ${overrideActive
          ? html`<button slot="secondaryAction" ?disabled=${this._busy} @click=${this._resume}>Resume schedule</button>`
          : html`<button slot="secondaryAction" @click=${this._close}>Cancel</button>`}
        <button slot="primaryAction" class="primary" ?disabled=${this._busy} @click=${this._confirm}>
          Hold
        </button>
      </ha-dialog>
    `;
  }

  static styles = [
    dialogStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];
}

if (!customElements.get("scheduled-climate-override-dialog")) {
  customElements.define(
    "scheduled-climate-override-dialog",
    ScheduledClimateOverrideDialog,
  );
}
