import { LitElement, css, html, nothing } from "lit";
import type { HomeAssistant, ScheduleDay } from "./types";
import { SCHEDULE_DAYS } from "./types";
import { DAY_GROUPS, DAY_LABELS } from "./schedule";
import { dialogStyles } from "./dialog-styles";

export interface CopyDestination {
  entityId: string;
  plan: string;
}

export interface CopyRequest {
  targetDays: ScheduleDay[];
  mode: "replace" | "merge";
  destination: CopyDestination;
}

interface DestinationOption {
  entityId: string;
  plan: string;
  label: string;
  disabled: boolean;
}

export class ScheduledClimateCopyDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    open: { attribute: false },
    sourceDay: { attribute: false },
    roomEntities: { attribute: false },
    planOptions: { attribute: false },
    currentEntityId: { attribute: false },
    currentPlan: { attribute: false },
    _selected: { state: true },
    _mode: { state: true },
    _destKey: { state: true },
  };

  hass?: HomeAssistant;
  open = false;
  sourceDay: ScheduleDay = "monday";
  roomEntities: string[] = [];
  planOptions: string[] = [];
  currentEntityId = "";
  currentPlan = "";
  private _selected: Set<ScheduleDay> = new Set();
  private _mode: "replace" | "merge" = "replace";
  private _destKey = "";
  private _wasOpen = false;

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open") && this.open && !this._wasOpen) {
      this._selected = new Set();
      this._mode = "replace";
      this._destKey = `${this.currentEntityId}::${this.currentPlan}`;
    }
    this._wasOpen = this.open;
  }

  private _destinations(): DestinationOption[] {
    const options: DestinationOption[] = [];
    for (const entityId of this.roomEntities) {
      const attrs = this.hass?.states[entityId]?.attributes;
      const friendly = attrs?.friendly_name ?? entityId;
      const schedules = attrs?.plan_schedules ?? {};
      const plans = attrs?.plan_options ?? this.planOptions;
      for (const plan of plans) {
        const single = this.roomEntities.length <= 1;
        const isCurrent =
          entityId === this.currentEntityId && plan === this.currentPlan;
        const label = single
          ? isCurrent
            ? `${plan} (this schedule)`
            : plan
          : `${friendly} · ${plan}${isCurrent ? " (this schedule)" : ""}`;
        options.push({
          entityId,
          plan,
          label,
          disabled: !isCurrent && !schedules[plan],
        });
      }
    }
    return options;
  }

  private _close(): void {
    this.open = false;
    this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: true, composed: true }),
    );
  }

  private _toggleDay(day: ScheduleDay, checked: boolean): void {
    const next = new Set(this._selected);
    if (checked) next.add(day);
    else next.delete(day);
    this._selected = next;
  }

  private _pick(days: ScheduleDay[]): void {
    this._selected = new Set(days.filter((day) => day !== this.sourceDay));
  }

  private _confirm(): void {
    const targetDays = SCHEDULE_DAYS.filter((day) => this._selected.has(day));
    if (targetDays.length === 0) return;
    const [entityId, plan] = this._destKey.split("::");
    this.dispatchEvent(
      new CustomEvent<CopyRequest>("copy", {
        bubbles: true,
        composed: true,
        detail: { targetDays, mode: this._mode, destination: { entityId, plan } },
      }),
    );
    this._close();
  }

  protected render() {
    if (!this.open) return nothing;
    const destinations = this._destinations();

    return html`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Copy ${DAY_LABELS[this.sourceDay]}</h2>
          </div>
          <div class="field">
            <span>Copy to days</span>
            <div class="chips">
              <button @click=${() => this._pick(DAY_GROUPS.all)}>All</button>
              <button @click=${() => this._pick(DAY_GROUPS.weekdays)}>Weekdays</button>
              <button @click=${() => this._pick(DAY_GROUPS.weekend)}>Weekend</button>
              <button @click=${() => (this._selected = new Set())}>Clear</button>
            </div>
            <div class="day-checks">
              ${SCHEDULE_DAYS.map(
                (day) => html`
                  <label>
                    <input
                      type="checkbox"
                      ?disabled=${day === this.sourceDay}
                      .checked=${this._selected.has(day)}
                      @change=${(event: Event) =>
                        this._toggleDay(
                          day,
                          (event.target as HTMLInputElement).checked,
                        )}
                    />
                    ${DAY_LABELS[day]}
                  </label>
                `,
              )}
            </div>
          </div>

          <div class="field">
            <span>How should existing blocks be handled?</span>
            <div class="radios">
              <label>
                <input
                  type="radio"
                  name="copy-mode"
                  ?checked=${this._mode === "replace"}
                  @change=${() => (this._mode = "replace")}
                />
                Replace
              </label>
              <label>
                <input
                  type="radio"
                  name="copy-mode"
                  ?checked=${this._mode === "merge"}
                  @change=${() => (this._mode = "merge")}
                />
                Merge
              </label>
            </div>
          </div>

          ${destinations.length > 1
            ? html`
                <label class="field">
                  <span>Destination schedule</span>
                  <select
                    .value=${this._destKey}
                    @change=${(event: Event) =>
                      (this._destKey = (event.target as HTMLSelectElement).value)}
                  >
                    ${destinations.map(
                      (option) => html`<option
                        value=${`${option.entityId}::${option.plan}`}
                        ?disabled=${option.disabled}
                      >
                        ${option.label}${option.disabled ? " — no schedule" : ""}
                      </option>`,
                    )}
                  </select>
                </label>
              `
            : nothing}

          <div class="dialog-actions">
            <button @click=${this._close}>Cancel</button>
            <button
              class="primary"
              ?disabled=${this._selected.size === 0}
              @click=${this._confirm}
            >
              Copy
            </button>
          </div>
        </div>
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

if (!customElements.get("scheduled-climate-copy-dialog")) {
  customElements.define(
    "scheduled-climate-copy-dialog",
    ScheduledClimateCopyDialog,
  );
}
