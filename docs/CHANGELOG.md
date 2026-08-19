# Changelog

All notable changes to Scheduled Climate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

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
