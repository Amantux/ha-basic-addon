# Copilot Instructions

## Repository overview

This repo ships two tightly coupled components under one GitHub URL:

| Component | Location | Purpose |
|---|---|---|
| HA Supervisor add-on | `config.json`, `build.json`, `Dockerfile`, `addon/` | Python stdlib HTTP service that exposes `/health` |
| Custom HA integration | `custom_components/ha_basic_addon/` | Polls the add-on and exposes a `sensor` entity via `DataUpdateCoordinator` |

`repository.json` and `hacs.json` are both at the repo root — the former makes the repo installable as a Supervisor add-on store, the latter makes it installable as a HACS integration.

---

## Architecture

### Add-on (`addon/main.py`)
- Pure Python stdlib — **no pip dependencies**. Keep it that way unless genuinely needed.
- Reads its runtime config from `/data/options.json` (injected by HA Supervisor at startup). Defaults are in `config.json` under `"options"`.
- Exposes `GET /` and `GET /health` returning JSON with `status`, `uptime`, `greeting`, `path`, `timestamp`.
- `run.sh` is the container entrypoint; the Dockerfile uses `ARG BUILD_FROM` and `FROM ${BUILD_FROM}` so the Supervisor can inject the correct HA base image at build time.

### Integration (`custom_components/ha_basic_addon/`)
Data flows in one direction:

```
config_flow.py  →  __init__.py  →  coordinator.py  →  sensor.py
```

- **`config_flow.py`** — two entry points: `async_step_user` (manual) and `async_step_discovery` (triggered by Supervisor when the add-on advertises `ha_basic_addon` via `"discovery"` in `config.json`).
- **`__init__.py`** — creates the `DataUpdateCoordinator`, calls `async_config_entry_first_refresh()`, stores it in `hass.data[DOMAIN][entry.entry_id]`, then sets up the `sensor` platform.
- **`coordinator.py`** — fetches `/health` every 60 s; raises `UpdateFailed` on `ClientError`.
- **`sensor.py`** — one entity (`HaBasicAddonSensor`); `native_value` is the `"status"` field; the remaining JSON fields become `extra_state_attributes`.
- **`helpers.py`** — single function `build_health_url(host, port)` used by both config_flow and coordinator. Normalises the host (adds `http://` if missing, strips trailing `/`).

---

## Key conventions

### Versioning — required on every push

**Bump the version on every commit that changes code or config.** HACS and the Supervisor only deliver updates when the version string increases. A push without a version bump will silently deliver no update to users.

Both files must be updated to the **same** value:
- `config.json` → `"version"`
- `custom_components/ha_basic_addon/manifest.json` → `"version"`

Use [semver](https://semver.org/): `MAJOR.MINOR.PATCH`
- `PATCH` — bug fixes, non-breaking tweaks (most common)
- `MINOR` — new endpoints, new sensors, new config options (backward-compatible)
- `MAJOR` — breaking changes to the API surface or config schema

Also add a bullet under a new `## [X.Y.Z] - YYYY-MM-DD` heading in `CHANGELOG.md` describing **what changed and why**.

Example workflow for any code change:
1. Make the code change.
2. Increment `"version"` in `config.json` and `manifest.json` (must match).
3. Add a `CHANGELOG.md` entry.
4. Commit and push — include the version number in the commit message, e.g. `fix: correct health timeout (v0.1.3)`.

### Supervisor add-on config rules
- Valid `config.json` keys: `name`, `version`, `slug`, `description`, `url`, `arch`, `startup`, `boot`, `options`, `schema`, `ports`, `ingress`, `map`, `discovery`.
- `map` must be a **string list**: `["data:rw"]`. Object form `[{"data": "config"}]` is rejected by Supervisor.
- Build settings live in `build.json`, **not** in `config.json`. The `build` key in `config.json` is invalid.
- `Dockerfile` must start with `ARG BUILD_FROM` / `FROM ${BUILD_FROM}` — the Supervisor passes the arch-appropriate base image via `--build-arg`.

### HACS metadata (`hacs.json`)
HACS v2 only accepts: `name`, `homeassistant`, `iot_class`. Keys like `domains`, `components`, `remote`, `tags`, `content_in_root` are invalid and will cause HACS to reject the repository.

### Integration entity style
Use `_attr_*` attribute assignment (dataclass style) in entity constructors rather than property overrides:
```python
self._attr_unique_id = f"{DOMAIN}_health"
self._attr_name = "Basic Add-on Health"
```

### Discovery wiring
For discovery to work end-to-end:
1. `config.json` must list the domain under `"discovery"`: `["ha_basic_addon"]`
2. `config_flow.py` must implement `async_step_discovery`
3. The config flow domain must match `DOMAIN` in `const.py` and `"domain"` in `manifest.json`

---

## HA best practices

These are non-obvious patterns enforced by the HA architecture that differ from generic Python.

### Always use `async_setup_platforms` / `async_unload_platforms`
Platform setup and teardown must go through the config entry helpers (already wired in `__init__.py`). Do not call `hass.helpers.discovery.async_load_platform` directly.

### Coordinator is the single source of truth
All entities should be `CoordinatorEntity` subclasses. Never fetch data directly in an entity — add a method to the coordinator and call it from there.

### Raise `UpdateFailed`, not bare exceptions
`coordinator.py` must catch network/parse errors and re-raise as `UpdateFailed`. Any other exception propagates to HA's error handler and disables the integration.

### `unique_id` must be stable
`_attr_unique_id` must not change across restarts. It is used by the entity registry to track the entity across renames and config changes. Use `f"{DOMAIN}_<stable_key>"`.

### Config entry data vs. options
- `entry.data` — set at config-flow time, does not change without re-auth/reconfiguration.
- `entry.options` — user-editable after setup via an options flow.
Currently everything lives in `entry.data`; add an options flow if user-tunable settings are needed post-setup.

### Type annotations
All new functions must carry full PEP 484 annotations. The file-level `from __future__ import annotations` is already present in every module — keep it.

### Logging
Use module-level `_LOGGER = logging.getLogger(__name__)`. Log at `DEBUG` for routine polling, `WARNING` for recoverable errors, `ERROR` only for failures that require user action.

---

## Local development

The add-on server can be run locally without Docker:
```bash
cd addon
python main.py          # listens on 0.0.0.0:8080 with hardcoded defaults
```

Smoke-test the health endpoint:
```bash
curl http://localhost:8080/health
```

The integration has no test suite. To validate integration Python syntax:
```bash
python -m compileall custom_components/ha_basic_addon
```
