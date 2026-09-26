# Scheduled Climate

Scheduled Climate is a Home Assistant custom integration that wraps existing climate entities with weekly schedules built on the Home Assistant schedule helper, persistent one-shot timers, temporary holds, and a matching dashboard card.

One config entry describes a **room**. A room can hold several climate entities — a mini split and a radiant heater, say — and several named **plans**, such as a `Winter` plan that heats and a `Summer` plan that cools. A `select` entity chooses the active plan, either by hand, from an automation, or automatically from an outdoor temperature sensor with hysteresis.

Requires Home Assistant 2026.1 or newer. Local integration branding is available on Home Assistant 2026.3 or newer.

## Showcase

| Full climate and schedule controls | Compact card and visual editor |
| --- | --- |
| <img src="docs/images/dashboard-standard.png" alt="Scheduled Climate standard dashboard card" width="560"> | <img src="docs/images/card-editor.png" alt="Scheduled Climate visual card editor with compact preview" width="560"> |

Edit weekly blocks from the dashboard, including HVAC mode, temperature or range setpoints, fan mode, and humidity:

<p align="center">
  <img src="docs/images/schedule-editor.png" alt="Scheduled Climate weekly schedule block editor" width="620">
</p>

See the **[complete user guide](docs/USER_GUIDE.md)** for installation, configuration screenshots, card options, rooms and plans, schedule behavior, holds, timer automations, permissions, migration, diagnostics, and troubleshooting. See the **[changelog](docs/CHANGELOG.md)** for release history.

## Installation

1. Add this repository to HACS as a custom integration.
2. Install **Scheduled Climate** and restart Home Assistant.
3. Open **Settings > Devices & services > Add integration**, select **Scheduled Climate**, name the room, and choose its first climate entity.

Add more climate entities, plans and schedule links afterwards from **Configure** on the entry.

The integration serves and registers its dashboard card automatically. A separate frontend download or Lovelace resource is not required.

Each climate entity you add is mirrored by a Scheduled Climate entity, and the original is hidden while it is wrapped so thermostats do not appear twice. Hiding is a user-interface concern only — automations, history and the APIs keep using the original entity — and it is reversed if you remove the target or uninstall the integration. Turn off **Wrapped entities** in the options to keep both visible.

![Add Scheduled Climate configuration flow](docs/images/integration-setup.png)

## Dashboard Card

Add the card through the dashboard visual editor or use YAML:

```yaml
type: custom:scheduled-climate-card
entity: climate.living_room_scheduled
name: Living room
layout: compact
timer_presets:
  - 15
  - 30
  - 60
  - 120
show_plan: true
show_schedule: true
schedule_editable: true
show_override: true
default_schedule_day: monday
default_plan: Winter
show_timer: true
```

The card derives all schedule, plan, hold and timer state from the wrapper entity, and reads the rest of the room from that entity's siblings, so one card covers a room with several devices. It displays only climate controls supported by the selected target, including HVAC mode, target temperature, preset, fan, swing, and humidity controls where available.

The card itself stays compact — room name, active plan, next change, target switcher, controls, **Hold** and the timer row. The full weekly editor opens in a dialog with a 7×24h week timeline, plan tabs and target tabs.

The `layout` option accepts `standard` (the default) or `compact`. Compact layout removes the circular temperature dial while retaining touch-friendly temperature and HVAC controls. Optional sections can each be collapsed; their states are retained per entity in the current browser.

Set `schedule_editable: false` to render the schedule read-only. Editing is always read-only for non-administrators, because Home Assistant restricts the schedule helper's create, update and delete WebSocket commands to administrators. `default_schedule_day` selects the day shown first, and `default_plan` the plan shown first; the current day and the active plan are used when they are omitted.

![Compact Scheduled Climate dashboard card](docs/images/dashboard-compact-mobile.png)

## Weekly Schedule

A Home Assistant **schedule** helper stores a flat set of values per time block, so it cannot describe two devices at once. Scheduled Climate therefore links **one helper per target and plan pair**. Every time block in a helper can carry climate settings as block data:

| Key | Meaning |
| --- | --- |
| `hvac_mode` | HVAC mode to select while the block is active |
| `temperature` | Single target temperature |
| `target_temp_low` / `target_temp_high` | Target temperature range (set both) |
| `fan_mode` | Fan mode |
| `humidity` | Target humidity |

Link a helper from the integration options, or create and link one directly from the schedule dialog. The HVAC mode is always applied before setpoints. When a block omits the mode, the most recently active supported mode is restored, falling back to the configured default. Outside every block the wrapper turns the target off, or leaves it untouched when **When no block is active** is set to `ignore`. These settings are per target, so one device in a room can be paused while another keeps running.

Copying a day takes any combination of days at once, with `All`, `Weekdays` and `Weekend` quick picks and a choice of `Replace` or `Merge`. A day can also be copied into another plan or another target.

Blocks that request a setting the target entity cannot accept are applied as far as possible; the unsupported parts are skipped, logged, and surfaced as a repair issue.

Upgrading from a release that used a single daily on and off time keeps those times visible on the wrapper entity and raises a repair issue. Use the **Create schedule** button to convert them into a weekly schedule, or link an existing helper from the options.

## Plans

Each room exposes `select.<room>_schedule_plan`, whose options are every plan name plus **Automatic** when an automatic rule is configured. Whatever that select holds is what the whole room follows.

Give each plan the outdoor temperature at or above which it takes over and the plans form ascending bands. A configurable hysteresis keeps the active plan until the reading leaves its band by half that width, and a sustain window makes a new band hold for a while before the plan actually switches. Choosing a plan by hand overrides the sensor until **Automatic** is selected again.

## Holds

A hold parks one target at settings of your choosing and suspends its schedule, either until the next scheduled change or for a bounded length of time. Holds persist across restarts, and are available to **every** user — this is how household members without an administrator account change the heating, since Home Assistant will not let a non-administrator edit a schedule helper.

## Timers

Only one timer is active per target. Starting a new on or off timer replaces the current timer and clears any running hold. Timer deadlines are stored in UTC and survive restart. An overdue timer executes once when Home Assistant starts and is then cleared.

Services:

- `scheduled_climate.start_on_timer`
- `scheduled_climate.start_off_timer`
- `scheduled_climate.cancel_timer`
- `scheduled_climate.link_schedule`
- `scheduled_climate.enable_schedule`
- `scheduled_climate.disable_schedule`
- `scheduled_climate.set_override`
- `scheduled_climate.clear_override`
- `scheduled_climate.select_plan`

Timer start services require a positive `duration`. `link_schedule` takes the storage `schedule_id` of a schedule helper and an optional `plan` name, and enables the schedule; call it without an id to unlink. `set_override` takes `until_next_block` or a `duration` plus the settings to hold. `select_plan` takes a plan name or `automatic`.

## Troubleshooting

- If the card is not listed after installation, restart Home Assistant and force-refresh the browser. The integration registers a content-versioned module URL automatically.
- If the wrapper is unavailable, verify that its selected target climate entity still exists and is available.
- If an on action does nothing, confirm that the target exposes at least one HVAC mode other than `off`.
- Reconfigure renames the room; change, add or remove its climate entities from **Configure** on the entry.
- If a plan never switches automatically, check that its outdoor temperature sensor reports a number and that the sustain window has elapsed.
- Enable debug logging for `custom_components.scheduled_climate` when reporting a service or callback failure.

## Development

Backend validation runs on Linux because Home Assistant requires POSIX modules unavailable in native Windows test runs:

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.13-bookworm sh -c "set -e; pip install 'homeassistant>=2026.1.0' 'pytest-homeassistant-custom-component>=0.13.200' 'pytest-cov>=6.0' --quiet; python -m pytest -q"
```

Build the card from `frontend`:

```powershell
npm install
npm run check
npm test
npm run build
```

The production bundle is written to `custom_components/scheduled_climate/frontend/scheduled-climate-card.js`.

## License

Scheduled Climate is available under the [MIT License](LICENSE).
