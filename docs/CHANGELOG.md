# Changelog

All notable changes to Scheduled Climate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Plans can now name an upper outdoor temperature bound.** A plan previously could only say "activate at or above this temperature", so a cold-weather plan such as frost protection could only be expressed indirectly by putting thresholds on every *other* plan. A plan can now name a lower bound, an upper bound, both, or neither: `below 2` for a frost plan, `8` to `16` for a shoulder-season plan, and no bounds for the room's fallback. Bands are half open, so neighbours sharing a boundary never overlap, and where bands do overlap the more specific one wins. The hysteresis dead zone applies to both ends of a band. Existing plans are unaffected — a plan with only a lower bound behaves exactly as before.

### Changed

- **The wrapped climate entities are now hidden by default.** Each target is mirrored by a Scheduled Climate entity, so leaving both visible showed every thermostat twice in entity pickers, voice assistants and auto-generated dashboards. The original entity is now hidden while a wrapper exists, matching how Home Assistant's own `switch_as_x` integration handles wrapped entities. Hiding affects the user interface only — automations, scripts, history and the REST and websocket APIs keep addressing the original entity exactly as before. The original is revealed again if the target is removed from the room, if the integration is uninstalled, or if you turn the new **Wrapped entities** option off. An entity you hid yourself is never touched.

### Fixed

- Target chips on the card, and the target tabs in the schedule and copy dialogs, repeated the room name on every entry — a room called `Family Room Climate Schedule` produced chips reading `Family Room Climate Schedule Minisplit`, which truncated and hid the part that actually distinguishes them. The wrapper entity now publishes a `target_name` attribute holding just the target's own name, and the card uses it.
- The schedule, copy and hold dialogs rendered their action buttons through Home Assistant's `primaryAction` and `secondaryAction` dialog slots, which current releases no longer render. The buttons collapsed to zero size, so **a hold or a day copy could not be confirmed from the dashboard at all**. Every dialog action is now drawn inside the dialog body.
- The card test suite opened the schedule editor on the current day but only defined blocks for Monday, so it passed from Monday to Friday and failed at the weekend. The clock is now pinned.

### Dependencies

- Bumped `vitest` and `@vitest/mocker` from 3.2.7 to 5.0.1 (#4).

## [2.0.0] - 2026-09-21

### Added

- **Rooms with several climate entities.** A config entry now describes a room that can hold more than one climate entity — a mini split and a radiant heater, for example. Each target gets its own wrapper `climate` entity, and they all share a single device. Targets are added, renamed, re-pointed and removed from the integration options.
- **Multiple schedule plans per room.** A room can hold several named plans, such as a `Winter` plan that heats and a `Summer` plan that cools. Each plan links its own schedule helper per target, so two devices in one room can keep completely different weekly shapes.
- **A `select` entity for the active plan.** `select.<room>_schedule_plan` is the single source of truth for which plan the room follows, so automations, scripts and voice assistants can switch plans. The new `scheduled_climate.select_plan` service does the same thing by plan name.
- **Automatic plan selection from an outdoor temperature sensor.** Plans can declare the outdoor temperature at or above which they take over. A configurable hysteresis band stops the selection flapping at a boundary, and a sustain window ignores brief excursions. Selecting a plan by hand overrides the sensor until `Automatic` is chosen again.
- **Temporary holds, usable by non-administrators.** `scheduled_climate.set_override` parks a target at chosen settings either until the next scheduled change or for a bounded length of time, and `scheduled_climate.clear_override` hands control straight back to the schedule. Holds are persisted, so they survive a restart. Because Home Assistant restricts schedule helper edits to administrators, this is how household members influence heating without an administrator account.
- **Copying a day to several days at once.** The card's copy dialog takes any combination of days, with `All`, `Weekdays` and `Weekend` quick picks, and offers `Replace` or `Merge`; merging reports the days where a block was dropped because it overlapped. A day can also be copied into another plan or another target.
- New repair issues for a room with no plans and for an outdoor temperature sensor that stopped reporting a number.
- `scheduled_climate.link_schedule` gained an optional `plan` field so a helper can be linked to a plan that is not the active one.

### Changed

- **The dashboard card was split up.** The card itself is now a slim status and control surface — room name, active plan, next change, target switcher, climate controls, hold button and timer. The full weekly editor moved into a dialog with a 7×24h week timeline, plan tabs and target tabs, which keeps the card usable as the feature set grows.
- Config entries migrate to version 3. A single-entity entry becomes a room holding one target and one plan named `Default`. The lone target keeps the entry id as its key, so the existing wrapper entity, its history and any dashboards referring to it are untouched.
- `enable_schedule` and `disable_schedule` now act on the single target they are aimed at rather than the whole entry, so one device in a room can be paused while another keeps running.
- The options flow is now a menu covering targets, plans, schedule links, plan selection and hold limits. The reconfigure flow now only renames the room; targets are managed from the options.
- Repair issue ids for schedule problems now include the target key, and their `{name}` placeholder is the target name rather than the entry title.
- Non-administrators now see the full weekly schedule read-only instead of an empty section, and keep access to holds, pause/resume and timers.

### Fixed

- A wrapper entity could advertise an incomplete list of its room's entities during startup, because the list was read from the entity registry before every sibling had been registered.
- The wrapper entity's attributes could still report an active hold immediately after a timer fired and cleared it.
- A config entry renamed in the Home Assistant UI kept a stale name in its stored data. On upgrade that stale name was applied to the migrated target, which appended it to the wrapper entity's friendly name — an entry renamed to `Lounge` would have shown `Lounge Living Room`. The lone target is now named after the entry title.
- Hand-edited or half-migrated config entry options raised `AttributeError` instead of falling back to defaults, which failed the entry setup and also broke the options flow needed to repair it.
- Closing the schedule editor while it was still loading left a websocket subscription running for the lifetime of the dashboard.
- A schedule helper edited elsewhere while the editor was open could reorder a day's blocks, so saving or deleting acted on the wrong block. Blocks are now matched by value rather than by position.
- The schedule, copy and hold dialogs showed no title, because Home Assistant's `ha-dialog` does not render its `heading` attribute in current releases. Each dialog now draws its own title.

## [1.1.1] - 2026-08-18

### Fixed

- The dashboard card is now registered as a persisted Lovelace dashboard resource instead of the in-memory extra-module-url list. The previous approach left a window on every Home Assistant restart where a client could load a dashboard before the integration finished registering the card, which is what caused it to intermittently fail to load — most visibly in the Android companion app, whose long-lived WebView rarely reloads past that window. The resource is now read from storage on every dashboard load, independent of this integration's own startup timing.

### Added

- A tag-triggered `Release` GitHub Actions workflow (`.github/workflows/release.yml`) that validates the backend and frontend, rebuilds the card bundle, and publishes the GitHub Release that HACS requires.

## [1.1.0] - 2026-08-15

### Added

- `scheduled_climate.enable_schedule` and `scheduled_climate.disable_schedule` services to pause or resume a linked schedule without unlinking it.
- A pause/resume toggle button in the dashboard card's schedule section, shown whenever a schedule is linked.

### Fixed

- The dashboard card could intermittently fail to load after a Home Assistant restart. Frontend resource registration moved from config-entry setup to component setup, and registration state is now tracked so a partial failure retries instead of leaving the card unreachable until the next restart.

## [1.0.0] - 2026-08-15

Initial release.
