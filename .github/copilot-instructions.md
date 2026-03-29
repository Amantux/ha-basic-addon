# Copilot Instructions

## ⚠️ CRITICAL: Change policy for this repository

**This repository (`ha-basic-addon`) is a stable reference implementation. It must NOT be modified without the user's explicit, expressed permission.**

Before making ANY change to `ha-basic-addon` — including Dockerfile, `run.sh`, `main.py`, the integration, config files, or documentation — you must:
1. **Stop.**
2. **Ask the user directly**: "I need to modify ha-basic-addon to do X. Do I have your permission?"
3. **Wait for a clear "yes"** before touching any file in this repo.

This repo exists as the proven, working foundation. It is also the reference that `ha-mcp-bridge` is built from. Unsolicited changes break that reference and cause cascading regressions (see v0.1.11, v0.1.12 history).

### Using ha-basic-addon as a foundation for ha-mcp-bridge
When building or improving `ha-mcp-bridge`:
- **Read** `ha-basic-addon`'s files to understand the correct patterns (Dockerfile, `run.sh`, `main.py`, `config_flow.py`, coordinator, translations).
- **Copy and adapt** those patterns into `ha-mcp-bridge` — do not modify the source.
- Any pattern that works in `ha-basic-addon` is the correct pattern for `ha-mcp-bridge`. Any deviation requires a documented reason.

---

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

The CI workflow (`.github/workflows/validate.yml`) enforces this: it will fail the build if the two version strings differ, and automatically creates a tagged GitHub release for any new version. **HACS requires a GitHub release to deliver updates to users** — without a matching tag, installed copies never see the update.

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

### `iot_class` must match actual behaviour
`manifest.json → iot_class` must reflect how the integration actually retrieves data:
- `local_polling` — integration polls the device on a schedule (current pattern, 60s coordinator)
- `local_push` — device pushes state changes to HA
Using the wrong value causes HACS/HA quality-scale warnings and misleads users.

### Discovery wiring — two-step `hassio` flow (Mealie pattern)

HA Supervisor sets `context={"source": SOURCE_HASSIO}` → calls `async_step_hassio`. **Do not create the entry in this step.** The correct pattern (from `homeassistant/components/mealie/config_flow.py`) is two steps:

1. `async_step_hassio` — set unique_id, abort if already configured, store `discovery_info`, redirect to `async_step_hassio_confirm`.
2. `async_step_hassio_confirm` — shows a confirmation card in the UI ("New device found"). User clicks it, sees the add-on name, confirms → validate connection → create entry.

Without `hassio_confirm`, HA silently auto-creates or silently fails with no visible notification. The confirmation step is what surfaces the "New device found" card in Settings → Devices & Services.

Citation: `homeassistant/components/hassio/discovery.py` → `discovery_flow.async_create_flow(..., context={"source": config_entries.SOURCE_HASSIO}, ...)`

**Import path** for `HassioServiceInfo` (not `homeassistant.components.hassio`):
```python
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
```
`HassioServiceInfo` fields: `config: dict`, `name: str`, `slug: str`, `uuid: str`

**Correct pattern:**
```python
_hassio_discovery: HassioServiceInfo | None = None  # class attribute

async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> FlowResult:
    await self.async_set_unique_id(discovery_info.uuid)
    self._abort_if_unique_id_configured()
    self._hassio_discovery = discovery_info
    return await self.async_step_hassio_confirm()

async def async_step_hassio_confirm(self, user_input=None) -> FlowResult:
    assert self._hassio_discovery is not None
    if user_input is None:
        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"addon": self._hassio_discovery.name},
        )
    port = int(self._hassio_discovery.config.get(CONF_PORT, DEFAULT_PORT))
    data = {CONF_HOST: DEFAULT_HOST, CONF_PORT: port}
    try:
        await self._async_validate_input(self.hass, data)
    except (ClientError, asyncio.TimeoutError):
        return self.async_abort(reason="cannot_connect")
    return self.async_create_entry(title=self._hassio_discovery.name, data=data)
```

Note: `discovery_info.config["host"]` is the bind address (`0.0.0.0`) — not routable. Connect via `DEFAULT_HOST` (`http://127.0.0.1`) since both HA and the add-on run on the same Supervisor host.

For discovery to work end-to-end:
1. `config.json` must list the domain under `"discovery"`: `["ha_basic_addon"]`
2. `config_flow.py` must implement both `async_step_hassio` AND `async_step_hassio_confirm`
3. `strings.json` must have a `config.step.hassio_confirm` entry with a `description` using `{addon}` placeholder
4. The config flow domain must match `DOMAIN` in `const.py` and `"domain"` in `manifest.json`

---

## HA best practices

These are non-obvious patterns enforced by the HA architecture that differ from generic Python.

### Always use `async_forward_entry_setups` / `async_unload_platforms`
Platform setup must use the `await`-able `async_forward_entry_setups` (introduced HA 2022.6). The old `async_setup_platforms` (non-awaited) is removed in modern HA.

```python
PLATFORMS = ["sensor"]

async def async_setup_entry(hass, entry):
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

Define `PLATFORMS` as a module-level list so it stays in sync between setup and unload.

### Never use `CONNECTION_CLASS`
`CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL` was removed in HA 2022.9. Delete it if present — its presence raises an `AttributeError` on modern HA.

### Use `aiohttp.ClientTimeout`, not raw integers
Raw `timeout=10` triggers a `DeprecationWarning` in modern aiohttp and may be removed. Always use `ClientTimeout`:
```python
from aiohttp import ClientTimeout
_TIMEOUT = ClientTimeout(total=10)
# ...
session.get(url, timeout=_TIMEOUT)
```
Define `_TIMEOUT` at module level so it is created once. Catch both `ClientError` and `asyncio.TimeoutError` since `ClientTimeout` raises the latter on expiry.

### Coordinator is the single source of truth
All entities should be `CoordinatorEntity` subclasses. Never fetch data directly in an entity — add a method to the coordinator and call it from there.

### Raise `UpdateFailed`, not bare exceptions
`coordinator.py` must catch network/parse errors and re-raise as `UpdateFailed`. Any other exception propagates to HA's error handler and disables the integration.

### `unique_id` must be stable
`_attr_unique_id` must not change across restarts. It is used by the entity registry to track the entity across renames and config changes. Use `f"{DOMAIN}_<stable_key>"`.

### Config entry data vs. options
- `entry.data` — set at config-flow time, does not change without re-auth/reconfiguration.
- `entry.options` — user-editable after setup via an options flow (implemented).
- When options change, the reload listener in `__init__.py` triggers `async_reload`, which recreates the coordinator with the new `update_interval`.

### Adding new options
1. Add the constant to `const.py`.
2. Add the field to `HaBasicAddonOptionsFlow.async_step_init` schema in `config_flow.py`.
3. Read it in the coordinator or wherever it applies.
4. Add the label to `strings.json` under `options.step.init.data`.

### Type annotations
All new functions must carry full PEP 484 annotations. The file-level `from __future__ import annotations` is already present in every module — keep it.

### Logging
Use module-level `_LOGGER = logging.getLogger(__name__)`. Log at `DEBUG` for routine polling, `WARNING` for recoverable errors, `ERROR` only for failures that require user action.

---

## CI / release workflow

`.github/workflows/validate.yml` runs on every push to `master`:

1. **Validate** — fails the build if `config.json` and `manifest.json` versions don't match.
2. **Release** — creates a tagged GitHub release (`v0.1.x`) and extracts the matching `CHANGELOG.md` section as release notes. Skips silently if the tag already exists.

HACS checks GitHub releases to know when a new version is available. Without a release tag that matches `manifest.json → version`, users who installed the integration via HACS will never receive the update.

---

## strings.json

`custom_components/ha_basic_addon/strings.json` provides user-facing text for the config flow. Without it, HA displays raw translation keys (`cannot_connect`, `already_configured`) in the UI.

Structure mirrors the config flow steps and matches keys used in `config_flow.py`:
- `config.step.<step_id>.data.<key>` → label for each form field
- `config.error.<key>` → shown when `errors["base"] = "<key>"` is set
- `config.abort.<key>` → shown when `async_abort(reason="<key>")` is called

When adding a new error or abort reason in `config_flow.py`, add the matching string here.

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
