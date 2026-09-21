import { css } from "lit";

/** Styling shared by the Scheduled Climate dialogs. */
export const dialogStyles = css`
  ha-dialog {
    --mdc-dialog-min-width: min(560px, 92vw);
    --mdc-dialog-max-width: min(640px, 96vw);
  }
  .content {
    display: grid;
    gap: 16px;
    color: var(--primary-text-color);
  }
  /* Home Assistant's ha-dialog does not reliably render its own heading text
     across versions, so each dialog draws its own title row. */
  .dialog-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dialog-title h2 {
    margin: 0;
    flex: 1;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: 500;
    color: var(--primary-text-color);
  }
  h4 {
    margin: 0;
    font-size: var(--ha-font-size-m, 14px);
  }
  p,
  .caption,
  .field > span {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: 12px;
  }
  .tabs,
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  .field {
    display: grid;
    gap: 5px;
  }
  label.field > span {
    font-size: 12px;
  }
  button {
    min-height: 40px;
    padding: 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-border-radius-pill, 999px);
    color: var(--primary-text-color);
    background: var(--card-background-color);
    font: inherit;
    cursor: pointer;
    text-transform: capitalize;
    white-space: nowrap;
  }
  button:hover {
    background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color));
  }
  button.selected,
  button.primary {
    color: var(--text-primary-color, white);
    background: var(--primary-color);
    border-color: var(--primary-color);
  }
  button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  button.icon {
    width: 40px;
    padding: 7px;
  }
  button ha-icon {
    --mdc-icon-size: 18px;
    margin-right: 6px;
    vertical-align: -4px;
  }
  button.icon ha-icon {
    margin: 0;
  }
  input,
  select {
    box-sizing: border-box;
    min-width: 0;
    min-height: 40px;
    padding: 7px 10px;
    color: var(--primary-text-color);
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-border-radius-md, 8px);
    font: inherit;
  }
  input[type="checkbox"],
  input[type="radio"] {
    min-height: 0;
    accent-color: var(--primary-color);
  }
  .radios {
    display: flex;
    gap: 16px;
  }
  .radios label,
  .day-checks label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    text-transform: none;
  }
  .day-checks {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .error {
    color: var(--error-color, #db4437);
    font-size: 12px;
  }
  .warning {
    color: var(--warning-color, #ffa600);
    font-size: 12px;
  }
`;
