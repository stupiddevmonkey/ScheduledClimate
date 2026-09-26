# GitHub Copilot Instructions

This repository contains a Home Assistant custom integration.

All code generated for this project must follow Home Assistant architectural patterns, Python best practices, and Home Assistant Integration Quality Scale recommendations.

## Core Principles

### Priorities

When making implementation decisions, prioritize:

1. Correctness
2. Reliability
3. Maintainability
4. Testability
5. Readability
6. Performance

Never sacrifice correctness for brevity.

### Architecture

Favor:

* Explicit code over clever code
* Composition over inheritance
* Strong typing over dynamic behavior
* Async APIs over synchronous APIs
* Immutable data structures where practical
* Separation of concerns
* Small focused modules

Avoid:

* Global mutable state
* Hidden side effects
* Circular imports
* Deep inheritance hierarchies
* Over-engineering
* Premature optimization

## Home Assistant Requirements

### Follow Home Assistant Patterns

Generated code should closely mirror patterns found in Home Assistant Core.

Use:

* `ConfigEntry`
* `DataUpdateCoordinator`
* `CoordinatorEntity`
* `ConfigFlow`
* Device Registry
* Entity Registry
* Translations
* Diagnostics
* Repairs
* Reauthentication flows

where appropriate.

Do not invent alternative architectures when Home Assistant already provides a standard solution.

### Async First

All integration code should be asynchronous unless a Home Assistant guideline explicitly requires otherwise.

Prefer:

```python
async def
```

over:

```python
def
```

Use:

```python
await hass.async\_add\_executor\_job(...)
```

for blocking I/O.

Never perform:

* Blocking network operations
* Blocking filesystem operations
* Long-running CPU work

inside the event loop.

### Config Entries Only

New integrations should support UI configuration through Config Flows.

Avoid YAML configuration unless explicitly required.

### Entity Design

Entities should:

* Expose only meaningful state
* Minimize unnecessary state updates
* Use proper device classes
* Use proper entity categories
* Use proper state classes
* Use translation keys

Avoid excessive attributes.

### Unique IDs

All entities must have stable unique IDs.

Unique IDs must:

* Be deterministic
* Survive restarts
* Survive upgrades

Never use:

* Entity names
* Random UUIDs generated at runtime

as unique IDs.

## Coordinator Pattern

Use `DataUpdateCoordinator` whenever data is fetched from an external service.

Coordinator responsibilities:

* API communication
* Polling
* Refresh management
* Error handling

Entities should primarily read coordinator data.

Avoid putting API logic inside entities.

Preferred structure:

```text
Entity
    ↓
Coordinator
    ↓
API Client
```

## API Client Design

Encapsulate external service communication in a dedicated client module.

Example:

```text
custom\_components/
    my\_integration/
        api.py
```

The API client should:

* Be fully typed
* Be async
* Raise meaningful exceptions
* Have minimal Home Assistant dependencies
* Be independently testable

Business logic belongs in the client layer, not entities.

## Typing Standards

All code must use type hints.

Required:

```python
def example(value: str) -> int:
```

Avoid:

```python
def example(value):
```

Use:

```python
from collections.abc import Mapping
from collections.abc import Callable
```

instead of older typing imports where appropriate.

Enable strict typing assumptions.

Avoid `Any` unless truly unavoidable.

## Dataclasses

Prefer dataclasses for structured data.

Example:

```python
@dataclass(slots=True, frozen=True)
class DeviceInfo:
    id: str
    name: str
```

Use immutable structures whenever practical.

## Constants

All constants belong in:

```text
const.py
```

Avoid magic strings throughout the codebase.

## Error Handling

Never swallow exceptions.

Bad:

```python
except Exception:
    pass
```

Use targeted exceptions.

Always provide context in logs.

## Logging Standards

Use:

```python
\_LOGGER = logging.getLogger(\_\_name\_\_)
```

Do not log secrets, tokens, passwords, API keys, or PII.

## Configuration Flow

Configuration flows should:

* Validate credentials
* Validate connectivity
* Handle duplicate entries
* Support reauthentication
* Surface user-friendly errors

## Translations

All user-facing text must be translatable.

## Diagnostics

Provide diagnostics support and redact sensitive information.

## Repairs

When issues can be detected automatically, prefer Repairs over logging alone.

## Tests

Every feature must include tests.
If docker is running, ensure that full integration tests are executed within the appropriate container environment.

### Minimum Expectations

* Unit tests
* Error-path tests
* Edge-case tests
* Regression tests for bug fixes

### Testing Framework

Use `pytest` and Home Assistant testing utilities.

### Coverage Expectations

Aim for high coverage of:

* API client
* Coordinator
* Config flow
* Entity behavior

## File Organization

```text
custom\_components/
└── my\_integration/
    ├── \_\_init\_\_.py
    ├── api.py
    ├── const.py
    ├── coordinator.py
    ├── config\_flow.py
    ├── diagnostics.py
    ├── entity.py
    ├── sensor.py
    ├── binary\_sensor.py
    ├── switch.py
    ├── button.py
    ├── device\_tracker.py
    ├── services.yaml
    ├── manifest.json
    └── translations/
```

## Dependencies

Prefer Home Assistant built-in helpers before introducing third-party dependencies.

## Code Review Expectations

Generated code should pass:

* Ruff
* Home Assistant linting
* Pytest
* Type checking

## Documentation

* All new features and changes must be documented in the appropriate sections of the project documentation. Include usage examples and configuration instructions where applicable.
* Any element that is documented and has a corresponding UI element should include a screenshot or visual reference in the documentation. Add helping text or annotations to the screenshot where necessary to clarify usage.

## Changelog

Always update `docs/CHANGELOG.md` with a summary of changes for every release. Continue updating the same changelog entry until the release is published. Use the following format:

```text
## [Unreleased]
### Added
### Changed
### Fixed

## Copilot Behavior Requirements

When generating code:

* Follow existing project structure first.
* Match existing naming conventions.
* Reuse existing patterns before introducing new ones.
* Update related tests whenever implementation changes.
* Generate production-quality code.
* Generate complete implementations rather than TODO placeholders.

When uncertain:

* Prefer Home Assistant Core conventions.
* Prefer consistency with existing repository patterns.

Never generate code that knowingly violates Home Assistant architecture guidelines or Integration Quality Scale recommendations.