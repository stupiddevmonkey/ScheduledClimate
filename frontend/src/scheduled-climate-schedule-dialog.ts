import { LitElement, css, html, nothing } from "lit";
import type {
  HassEntity,
  HomeAssistant,
  ScheduleDay,
  ScheduleItem,
  ScheduleTimeRange,
} from "./types";
import { SCHEDULE_DAYS } from "./types";
import type { BlockDraft } from "./schedule";
import {
  DAY_LABELS,
  buildUpdateMessage,
  copyDayToBlocks,
  describeBlock,
  draftToTimeRange,
  emptyDraft,
  findBlockIndex,
  shortTime,
  sortBlocks,
  timeRangeToDraft,
  todayDay,
  validateDraft,
  withDayBlocks,
} from "./schedule";
import { HOUR_TICKS, weekSegments } from "./timeline";
import { dialogStyles } from "./dialog-styles";
import "./scheduled-climate-copy-dialog";
import type { CopyRequest } from "./scheduled-climate-copy-dialog";

export class ScheduledClimateScheduleDialog extends LitElement {
  static properties = {
    hass: { attribute: false },
    entityId: { attribute: false },
    open: { attribute: false },
    initialTarget: { attribute: false },
    initialPlan: { attribute: false },
    _selectedTarget: { state: true },
    _selectedPlan: { state: true },
    _selectedDay: { state: true },
    _schedules: { state: true },
    _draft: { state: true },
    _error: { state: true },
    _warning: { state: true },
    _busy: { state: true },
    _loading: { state: true },
    _copyOpen: { state: true },
  };

  hass?: HomeAssistant;
  entityId?: string;
  open = false;
  initialTarget?: string;
  initialPlan?: string;

  private _selectedTarget = "";
  private _selectedPlan = "";
  private _selectedDay: ScheduleDay = todayDay();
  private _schedules: ScheduleItem[] = [];
  private _draft?: BlockDraft;
  private _error = "";
  private _warning = "";
  private _busy = false;
  private _loading = false;
  private _copyOpen = false;
  private _wasOpen = false;
  private _unsubscribe?: () => void;

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribe?.();
    this._unsubscribe = undefined;
  }

  protected willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("open")) {
      if (this.open && !this._wasOpen) this._onOpen();
      if (!this.open && this._wasOpen) {
        this._unsubscribe?.();
        this._unsubscribe = undefined;
      }
    }
    this._wasOpen = this.open;
  }

  private _onOpen(): void {
    const room = this._roomEntities();
    this._selectedTarget =
      this.initialTarget && room.includes(this.initialTarget)
        ? this.initialTarget
        : (this.entityId ?? room[0] ?? "");
    const plans = this._planOptions(this._selectedTarget);
    const active = this._targetState()?.attributes.active_plan ?? undefined;
    this._selectedPlan =
      this.initialPlan && plans.includes(this.initialPlan)
        ? this.initialPlan
        : active && plans.includes(active)
          ? active
          : (plans[0] ?? "");
    this._selectedDay = todayDay();
    this._draft = undefined;
    this._error = "";
    this._warning = "";
    void this._subscribe();
  }

  private get _isAdmin(): boolean {
    return this.hass?.user?.is_admin === true;
  }

  private _roomEntities(): string[] {
    const attrs = this.entityId
      ? this.hass?.states[this.entityId]?.attributes
      : undefined;
    const room = attrs?.room_entities;
    if (room && room.length > 0) return room;
    return this.entityId ? [this.entityId] : [];
  }

  private _planOptions(entityId: string): string[] {
    return this.hass?.states[entityId]?.attributes.plan_options ?? [];
  }

  private _targetState(): HassEntity | undefined {
    return this._selectedTarget
      ? this.hass?.states[this._selectedTarget]
      : undefined;
  }

  private _scheduleStorageId(): string | null {
    const schedules = this._targetState()?.attributes.plan_schedules ?? {};
    return schedules[this._selectedPlan] ?? null;
  }

  private _schedule(): ScheduleItem | undefined {
    const id = this._scheduleStorageId();
    if (!id) return undefined;
    return this._schedules.find((item) => item.id === id);
  }

  private async _subscribe(): Promise<void> {
    this._unsubscribe?.();
    this._unsubscribe = undefined;
    await this._loadSchedules();
    if (!this.hass?.connection) return;
    // The dialog can be closed while the awaits above are in flight. Its
    // element is never removed from the DOM, so a subscription stored after
    // that point would outlive the dialog and never be cleaned up.
    if (!this.open) return;
    try {
      const unsubscribe = await this.hass.connection.subscribeMessage(
        () => void this._loadSchedules(),
        { type: "schedule/subscribe" },
      );
      if (!this.open) {
        unsubscribe();
        return;
      }
      this._unsubscribe = unsubscribe;
    } catch {
      // Live updates are optional.
    }
  }

  private async _loadSchedules(): Promise<void> {
    if (!this.hass) return;
    this._loading = true;
    try {
      this._schedules = await this.hass.callWS<ScheduleItem[]>({
        type: "schedule/list",
      });
    } catch (error) {
      this._error =
        error instanceof Error ? error.message : "Unable to load schedules";
    } finally {
      this._loading = false;
    }
  }

  private _close(): void {
    this.open = false;
    this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: true, composed: true }),
    );
  }

  private _selectTarget(entityId: string): void {
    this._selectedTarget = entityId;
    const plans = this._planOptions(entityId);
    if (!plans.includes(this._selectedPlan)) {
      const active = this.hass?.states[entityId]?.attributes.active_plan;
      this._selectedPlan =
        active && plans.includes(active) ? active : (plans[0] ?? "");
    }
    this._draft = undefined;
    this._error = "";
    this._warning = "";
  }

  private _selectPlan(plan: string): void {
    this._selectedPlan = plan;
    this._draft = undefined;
    this._error = "";
    this._warning = "";
  }

  private _selectDay(day: ScheduleDay): void {
    this._selectedDay = day;
    this._draft = undefined;
    this._error = "";
  }

  private _dayBlocks(day: ScheduleDay = this._selectedDay): ScheduleTimeRange[] {
    return sortBlocks(this._schedule()?.[day] ?? []);
  }

  private async _writeSchedule(next: ScheduleItem): Promise<boolean> {
    if (!this.hass || this._busy) return false;
    // Home Assistant rejects schedule writes from non-administrators, so never
    // issue one; the editor is rendered read-only for them.
    if (!this._isAdmin) return false;
    this._busy = true;
    this._error = "";
    try {
      await this.hass.callWS(buildUpdateMessage(next));
      this._schedules = this._schedules.map((item) =>
        item.id === next.id ? next : item,
      );
      return true;
    } catch (error) {
      this._error =
        error instanceof Error ? error.message : "Unable to save the schedule";
      return false;
    } finally {
      this._busy = false;
    }
  }

  private async _saveDraft(): Promise<void> {
    const draft = this._draft;
    const schedule = this._schedule();
    if (!schedule || !draft) return;
    const blocks = this._dayBlocks();

    // Re-find the block being edited: a push from schedule/subscribe can have
    // reordered this day since the draft was opened.
    let index: number | null = null;
    if (draft.origin) {
      index = findBlockIndex(blocks, draft.origin);
      if (index < 0) {
        this._error =
          "That block changed somewhere else. Reopen it and try again.";
        this._draft = undefined;
        return;
      }
    }

    const resolved = { ...draft, index };
    const error = validateDraft(resolved, blocks);
    if (error) {
      this._error = error;
      return;
    }
    const next = [...blocks];
    if (index === null) next.push(draftToTimeRange(resolved));
    else next[index] = draftToTimeRange(resolved);
    if (
      await this._writeSchedule(withDayBlocks(schedule, this._selectedDay, next))
    ) {
      this._draft = undefined;
    }
  }

  private _duplicateBlock(block: ScheduleTimeRange): void {
    this._draft = { ...timeRangeToDraft(block, 0), index: null, origin: undefined };
    this._error = "";
  }

  private async _deleteBlock(block: ScheduleTimeRange): Promise<void> {
    const schedule = this._schedule();
    if (!schedule) return;
    const blocks = this._dayBlocks();
    const index = findBlockIndex(blocks, block);
    if (index < 0) {
      this._error = "That block changed somewhere else. Reopen it and try again.";
      return;
    }
    const next = blocks.filter((_, position) => position !== index);
    this._draft = undefined;
    await this._writeSchedule(withDayBlocks(schedule, this._selectedDay, next));
  }

  private _openBlock(day: ScheduleDay, index: number): void {
    this._selectedDay = day;
    if (!this._isAdmin) {
      this._draft = undefined;
      return;
    }
    const block = this._dayBlocks(day)[index];
    this._draft = block ? timeRangeToDraft(block, index) : undefined;
    this._error = "";
  }

  private _openEmptyDay(day: ScheduleDay): void {
    this._selectedDay = day;
    if (this._isAdmin) {
      this._draft = { ...emptyDraft(), index: null };
      this._error = "";
    }
  }

  private async _createSchedule(): Promise<void> {
    const target = this._targetState();
    if (!this.hass || !target || this._busy || !this._isAdmin) return;
    const message: Record<string, unknown> = {
      type: "schedule/create",
      name: `${target.attributes.friendly_name ?? this._selectedTarget} — ${this._selectedPlan}`,
    };
    for (const day of SCHEDULE_DAYS) message[day] = [];
    this._busy = true;
    this._error = "";
    let created: ScheduleItem | undefined;
    try {
      created = await this.hass.callWS<ScheduleItem>(message);
    } catch (error) {
      this._error =
        error instanceof Error ? error.message : "Unable to create the schedule";
    } finally {
      this._busy = false;
    }
    if (created) {
      try {
        await this.hass.callService("scheduled_climate", "link_schedule", {
          entity_id: this._selectedTarget,
          schedule_id: created.id,
          plan: this._selectedPlan,
        });
        await this._loadSchedules();
      } catch (error) {
        this._error =
          error instanceof Error ? error.message : "Unable to link the schedule";
      }
    }
  }

  private async _onCopy(event: CustomEvent<CopyRequest>): Promise<void> {
    this._copyOpen = false;
    const { targetDays, mode, destination } = event.detail;
    const sourceBlocks = this._dayBlocks();
    const destAttrs = this.hass?.states[destination.entityId]?.attributes;
    const destId = destAttrs?.plan_schedules?.[destination.plan] ?? null;
    const destSchedule =
      destId === this._scheduleStorageId()
        ? this._schedule()
        : this._schedules.find((item) => item.id === destId);
    if (!destSchedule) {
      this._error = "That schedule is not available yet.";
      return;
    }
    const { schedule, conflicts } = copyDayToBlocks(
      sourceBlocks,
      destSchedule,
      targetDays,
      mode,
    );
    this._warning = "";
    if (await this._writeSchedule(schedule)) {
      if (conflicts.length > 0) {
        this._warning = `Some blocks were skipped to avoid overlaps on ${conflicts
          .map((day) => DAY_LABELS[day])
          .join(", ")}.`;
      }
    }
  }

  private _renderTimeline(schedule: ScheduleItem) {
    const week = weekSegments(schedule);
    return html`
      <div class="timeline" role="grid" aria-label="Weekly schedule">
        <div class="axis">
          <span class="axis-label"></span>
          <div class="ticks">
            ${HOUR_TICKS.map(
              (hour) => html`<span
                class="tick"
                style="left:${(hour / 24) * 100}%"
                >${hour}</span
              >`,
            )}
          </div>
        </div>
        ${SCHEDULE_DAYS.map(
          (day) => html`
            <div class="row" role="row">
              <button
                class=${`day-name ${day === this._selectedDay ? "selected" : ""}`}
                @click=${() => this._selectDay(day)}
              >
                ${DAY_LABELS[day]}
              </button>
              <div
                class="track"
                @click=${() => this._openEmptyDay(day)}
              >
                ${week[day].map(
                  (segment) => html`<button
                    class="segment"
                    title=${`${shortTime(segment.from)} – ${shortTime(segment.to)} · ${segment.label}`}
                    style="left:${segment.startPercent}%;width:${segment.widthPercent}%"
                    @click=${(event: Event) => {
                      event.stopPropagation();
                      this._openBlock(day, segment.index);
                    }}
                  >
                    <span>${shortTime(segment.from)}</span>
                  </button>`,
                )}
              </div>
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderBlockList(state: HassEntity) {
    const blocks = this._dayBlocks();
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
                  ${this._isAdmin
                    ? html`
                        <button class="icon" title="Edit block" aria-label="Edit block" @click=${() => this._openBlock(this._selectedDay, index)}>
                          <ha-icon icon="mdi:pencil-outline"></ha-icon>
                        </button>
                        <button class="icon" title="Duplicate block" aria-label="Duplicate block" @click=${() => this._duplicateBlock(block)}>
                          <ha-icon icon="mdi:content-duplicate"></ha-icon>
                        </button>
                        <button class="icon" title="Delete block" aria-label="Delete block" @click=${() => this._deleteBlock(block)}>
                          <ha-icon icon="mdi:delete-outline"></ha-icon>
                        </button>
                      `
                    : nothing}
                </li>
              `,
            )}
      </ul>
      ${this._isAdmin
        ? html`
            <div class="actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => this._openEmptyDay(this._selectedDay)}>
                <ha-icon icon="mdi:plus"></ha-icon>Add block
              </button>
              <button ?disabled=${this._busy || this._dayBlocks().length === 0} @click=${() => (this._copyOpen = true)}>
                <ha-icon icon="mdi:content-copy"></ha-icon>Copy day
              </button>
            </div>
            ${this._draft ? this._renderDraft(state, this._draft) : nothing}
          `
        : nothing}
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
      <div class="grid draft">
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
        <div class="actions draft-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._saveDraft()}><ha-icon icon="mdi:content-save-outline"></ha-icon>Save block</button>
          <button ?disabled=${this._busy} @click=${() => (this._draft = undefined)}>Cancel</button>
        </div>
      </div>
    `;
  }

  private _renderMissing() {
    if (this._isAdmin) {
      return html`
        <div class="missing">
          <p class="caption">No schedule is linked to the “${this._selectedPlan}” plan for this target yet.</p>
          <button class="primary" ?disabled=${this._busy} @click=${() => this._createSchedule()}>
            <ha-icon icon="mdi:calendar-plus"></ha-icon>Create schedule for this plan
          </button>
        </div>
      `;
    }
    return html`<p class="caption">No schedule is linked to the “${this._selectedPlan}” plan yet. Ask an administrator to create one.</p>`;
  }

  protected render() {
    if (!this.open || !this.hass) return nothing;
    const room = this._roomEntities();
    const target = this._targetState();
    const plans = this._planOptions(this._selectedTarget);
    const schedule = this._schedule();

    return html`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Schedule</h2>
          </div>
          ${plans.length > 0
            ? html`<div class="tabs" role="tablist" aria-label="Plans">
                ${plans.map(
                  (plan) => html`<button
                    role="tab"
                    aria-selected=${plan === this._selectedPlan}
                    class=${plan === this._selectedPlan ? "selected" : ""}
                    @click=${() => this._selectPlan(plan)}
                  >${plan}</button>`,
                )}
              </div>`
            : nothing}
          ${room.length > 1
            ? html`<div class="tabs" role="tablist" aria-label="Targets">
                ${room.map(
                  (entityId) => html`<button
                    role="tab"
                    aria-selected=${entityId === this._selectedTarget}
                    class=${`ghost ${entityId === this._selectedTarget ? "selected" : ""}`}
                    @click=${() => this._selectTarget(entityId)}
                  >${this.hass?.states[entityId]?.attributes.friendly_name ?? entityId}</button>`,
                )}
              </div>`
            : nothing}

          ${schedule && target
            ? html`${this._renderTimeline(schedule)} ${this._renderBlockList(target)}`
            : this._scheduleStorageId()
              ? html`<p class="caption">${this._loading ? "Loading the schedule…" : "The linked schedule could not be found."}</p>`
              : this._renderMissing()}

          ${this._error ? html`<p class="error" role="alert">${this._error}</p>` : nothing}
          ${this._warning ? html`<p class="warning" role="status">${this._warning}</p>` : nothing}
        </div>

        <button slot="primaryAction" @click=${this._close}>Close</button>
      </ha-dialog>
      <scheduled-climate-copy-dialog
        .hass=${this.hass}
        .open=${this._copyOpen}
        .sourceDay=${this._selectedDay}
        .roomEntities=${room}
        .planOptions=${plans}
        .currentEntityId=${this._selectedTarget}
        .currentPlan=${this._selectedPlan}
        @copy=${this._onCopy}
        @dialog-closed=${() => (this._copyOpen = false)}
      ></scheduled-climate-copy-dialog>
    `;
  }

  static styles = [
    dialogStyles,
    css`
      :host {
        display: contents;
      }
      .tabs button.ghost {
        text-transform: none;
      }
      .timeline {
        display: grid;
        gap: 4px;
      }
      .axis,
      .row {
        display: grid;
        grid-template-columns: 52px 1fr;
        align-items: center;
        gap: 8px;
      }
      .ticks {
        position: relative;
        height: 14px;
      }
      .tick {
        position: absolute;
        transform: translateX(-50%);
        color: var(--secondary-text-color);
        font-size: 10px;
        font-variant-numeric: tabular-nums;
      }
      .day-name {
        min-height: 34px;
        padding: 4px 6px;
        font-size: 12px;
      }
      .track {
        position: relative;
        height: 34px;
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-border-radius-md, 8px);
        background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color)));
        overflow: hidden;
        cursor: pointer;
      }
      .segment {
        position: absolute;
        top: 3px;
        bottom: 3px;
        min-height: 0;
        min-width: 6px;
        padding: 0 4px;
        border: none;
        border-radius: 4px;
        color: var(--text-primary-color, white);
        background: var(--primary-color);
        font-size: 10px;
        text-align: left;
        overflow: hidden;
      }
      .segment span {
        pointer-events: none;
        font-variant-numeric: tabular-nums;
      }
      .day-chips {
        display: flex;
        gap: 6px;
        overflow-x: auto;
        padding-bottom: 2px;
        scrollbar-width: thin;
      }
      .day-chips button {
        flex: 1 0 auto;
        min-width: 46px;
      }
      .block-list {
        display: grid;
        gap: 8px;
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .block {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-border-radius-lg, 12px);
      }
      .block-copy {
        display: grid;
        flex: 1 1 auto;
        min-width: 0;
        gap: 2px;
      }
      .block-copy span {
        font-variant-numeric: tabular-nums;
      }
      .block-copy small {
        color: var(--secondary-text-color);
        font-size: 12px;
        text-transform: capitalize;
      }
      .block .icon {
        min-height: 36px;
        padding: 6px;
      }
      .grid.draft {
        padding: 12px;
        border-radius: var(--ha-border-radius-lg, 12px);
        background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color)));
      }
      .draft-actions {
        grid-column: 1 / -1;
      }
      .missing {
        display: grid;
        gap: 12px;
        justify-items: start;
      }
      @media (max-width: 480px) {
        .grid.draft {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];
}

if (!customElements.get("scheduled-climate-schedule-dialog")) {
  customElements.define(
    "scheduled-climate-schedule-dialog",
    ScheduledClimateScheduleDialog,
  );
}
