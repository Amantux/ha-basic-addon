# Changelog

## [0.1.11] - 2026-03-29
- **Fix (critical): s6-overlay Dockerfile.**
  HA base images use s6-overlay as PID 1 (`ENTRYPOINT ["/init"]`). The previous
  `Dockerfile` had `ENTRYPOINT ["./run.sh"]` which bypassed s6-overlay entirely →
  `s6-overlay-suexec: fatal: can only run as pid 1`.
  Fix: removed `ENTRYPOINT`; service script registered at
  `/etc/services.d/ha-basic-addon/run` so s6-overlay starts and supervises it.
- **Fix: `run.sh` shebang → `#!/usr/bin/with-contenv bashio`.**
  Ensures `SUPERVISOR_TOKEN` is exported from s6-overlay's container environment
  before Python starts. Without it discovery registration silently fails.
- **Fix: `pip` → `pip3`** in Dockerfile RUN command.

## [0.1.10] - 2026-03-29
- **Docs: Complete README rewrite.**
  - Three **Add to Home Assistant** one-click buttons:
    1. Add Supervisor repository (`my.home-assistant.io/redirect/supervisor_add_addon_repository`)
    2. Add integration via HACS (`my.home-assistant.io/redirect/hacs_repository`)
    3. Start config flow directly (`my.home-assistant.io/redirect/config_flow_start`)
  - Full end-to-end discovery chain diagram with ASCII art showing every hop from
    `register_discovery()` → Supervisor → `async_step_hassio` → `_set_confirm_only()` → badge.
  - "Why each step is necessary" table — documents every common failure mode and why the
    fix works.
  - "Why `translations/en.json` is required" explanation.
  - Entities table, options table, repository structure tree, local dev commands.

## [0.1.9] - 2026-03-29
- **Fix (root cause): Add-on now calls the Supervisor discovery API on startup.**
  Every previous version since v0.1.1 had `"discovery": ["ha_basic_addon"]` in
  `config.json` but `addon/main.py` never called `POST http://supervisor/discovery`.
  That declaration is only a *security allowlist* — it permits the call but does not
  make it automatically. Without the actual API call, Supervisor never tells HA core
  that the add-on is available, so `async_step_hassio` is *never triggered*, and
  every config_flow fix since v0.1.5 was solving the right problem in the wrong place.

  Fix: `register_discovery()` is now called at startup before the HTTP server starts.
  It POSTs `{"service": "ha_basic_addon", "config": {"host": "127.0.0.1", "port": 8080}}`
  to `http://supervisor/discovery` with `Authorization: Bearer {SUPERVISOR_TOKEN}`.
  Supervisor validates the service name against config.json, assigns a UUID, and
  notifies HA core → HA creates the config flow → `async_step_hassio` fires →
  the "New device found" card appears in Settings → Devices & Services.

- **Fix: Remove `ingress: true` from config.json.**
  Ingress requires the add-on to validate `X-Ingress-Token` on every request.
  Without that handler the add-on silently served malformed responses to Supervisor's
  ingress proxy. Removed since we are not building a sidebar panel.

## [0.1.8] - 2026-03-29
- **Fix (critical): `_set_confirm_only()` now called in `async_step_hassio_confirm`.**
  This is the single call that tells HA the confirmation form has no data fields — just
  a Submit button. HA uses this flag to surface the "New device found" notification badge
  in Settings → Devices & Services. Without it the flow is registered internally but the
  badge never appears, so the user has no idea the add-on was discovered.
  Source: https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/discovery/

- **Fix: Validation moved to `async_step_hassio` (not the confirm step).**
  Per the HA quality-scale discovery rule, the connection check happens in the *discovery*
  step, before any UI is shown. If the add-on is not yet ready, the flow aborts with
  `cannot_connect` immediately. The confirm step now only shows the form and creates the
  entry — no redundant re-validation needed.

- **Fix: `_abort_if_unique_id_configured(updates={CONF_PORT: port})`.**
  If the add-on is already configured but its port changed (e.g. after a restart with a
  different port), HA now silently updates the existing config entry instead of erroneously
  aborting as `already_configured`. This keeps the integration in sync automatically.

## [0.1.7] - 2026-03-29
- **Fix (critical): Add `translations/en.json`.**
  `strings.json` is the *source* file used by HA's translation toolchain. At runtime HA
  resolves UI strings from `translations/{lang}.json`. Without `translations/en.json`, config
  flow steps display raw translation keys instead of human-readable text, and some HA versions
  silently refuse to render the flow at all — making discovery invisible to the user.
  Fix: created `custom_components/ha_basic_addon/translations/en.json` mirroring `strings.json`
  with improved descriptions including `data_description` fields for every input.

- **Fix: `hacs.json` `iot_class` mismatch.**
  Was `local_push`; changed to `local_polling` to match `manifest.json`. HACS uses this field
  for integration categorisation and surfacing in search results.

- **Fix: Sensor `unique_id` now scoped to config entry.**
  Was a static `ha_basic_addon_health` string — a collision hazard if the integration is
  reloaded or added twice. Now `{entry.entry_id}_status` / `{entry.entry_id}_uptime`, ensuring
  stable, per-instance IDs in the HA entity and device registry.

- **Fix: `AddEntitiesCallback` import path.**
  Moved from deprecated `homeassistant.helpers.entity` to correct
  `homeassistant.helpers.entity_platform`.

- **Fix: `DeviceInfo` import path.**
  Moved from `homeassistant.helpers.entity` to `homeassistant.helpers.device_registry`
  (correct since HA 2023.x).

- **New: Two entities now exposed under one device card.**
  - `sensor.*_status` — health endpoint status text (`ok` / error string), with greeting /
    path / timestamp as state attributes.
  - `sensor.*_uptime` — add-on process uptime in seconds, typed as
    `SensorDeviceClass.DURATION` / `SensorStateClass.TOTAL_INCREASING` so HA can graph it.
  Both entities use `_attr_has_entity_name = True` and share a `DeviceInfo` keyed on
  `entry.entry_id`, producing a single device card in Settings → Devices & Services.

## [0.1.6] - 2026-03-29
- **Fix (critical): Two-step Supervisor discovery flow.**
  - Previous: `async_step_hassio` immediately called `async_create_entry`. This skipped the
    "New device found" notification in Settings → Devices & Services, gave the user no chance to
    confirm, and silently failed if the add-on wasn't ready yet.
  - Fixed: modelled after `homeassistant/components/mealie/config_flow.py`.
    `async_step_hassio` now stores `_hassio_discovery` and delegates to
    `async_step_hassio_confirm`. That step shows a confirmation form with the add-on name; on
    submit it validates the connection and only then creates the entry. If the connection fails,
    it aborts with `"cannot_connect"` instead of creating a broken entry.
  - Added `hassio_confirm` step to `strings.json` with `{addon}` placeholder.
  - Added `"cannot_connect"` abort reason to `strings.json`.
- Updated `copilot-instructions.md` with the Mealie two-step pattern for future reference.

## [0.1.5] - 2026-03-29
- **Fix (critical): Supervisor discovery now actually works.**
  - Renamed `async_step_discovery` → `async_step_hassio`. HA Supervisor sets
    `context["source"] = SOURCE_HASSIO` which maps to `async_step_hassio`, not
    `async_step_discovery`. The old handler was silently never called.
    Citation: `homeassistant/components/hassio/discovery.py` → `async_create_flow`
    with `context={"source": config_entries.SOURCE_HASSIO}`.
  - Import `HassioServiceInfo` from the correct path:
    `homeassistant.helpers.service_info.hassio` (not `homeassistant.components.hassio`).
  - Use `discovery_info.uuid` as the unique_id (stable per add-on instance) instead
    of the domain string. Using the domain caused all installs to share one unique_id.
  - Stop using `discovery_info.config["host"]` (that is the add-on bind address `0.0.0.0`,
    not a routable address). Discovery now defaults to `http://127.0.0.1`.
- **New: options flow** — users can now change the poll interval (10–3600 s) via
  Settings → Devices & Services → Configure, without re-adding the integration.
  Changing the option reloads the config entry so the new interval takes effect immediately.
- `const.py`: added `CONF_UPDATE_INTERVAL` / `DEFAULT_UPDATE_INTERVAL = 60`.
- `strings.json`: added `options.step.init` section for the new options form.

## [0.1.4] - 2026-03-29
- Fix: `addon/run.sh` now calls `python3` instead of `python` — HA Alpine base images only provide `python3`, so the add-on was failing to start.
- Fix: `iot_class` corrected from `local_push` to `local_polling` in `manifest.json` — the integration polls every 60s, it does not receive pushed data.
- Add: `homeassistant: "2022.6.0"` minimum version to `manifest.json` for HACS compatibility checking.
- Fix: `coordinator.py` now uses `aiohttp.ClientTimeout(total=10)` instead of a raw integer, and catches both `ClientError` and `asyncio.TimeoutError`. Logger renamed to `_LOGGER` per conventions. Import order corrected (stdlib before third-party).
- Fix: `config_flow.py` — removed deprecated `CONNECTION_CLASS`; discovery step now sets a stable unique_id via `async_set_unique_id(DOMAIN)` and calls `_abort_if_unique_id_configured()` to prevent duplicate entries; `ClientTimeout` used for validation request; `async_step_user` now has a full return type annotation.
- Fix: `sensor.py` — removed dead `ATTR_ATTRIBUTION` import; `async_setup_entry` now carries full type annotations using `AddEntitiesCallback`.

## [0.1.3] - 2026-03-29
- Fix: replace deprecated `async_setup_platforms` with `async_forward_entry_setups` (HA 2022.6+ requirement).
- Add `strings.json` so config flow shows human-readable labels and error messages instead of raw keys.
- Add `.github/workflows/validate.yml`: validates `config.json` and `manifest.json` versions match on every push, and auto-creates a GitHub release (required for HACS to deliver updates to users).

## [0.1.2] - 2026-03-29
- **Fix: valid Supervisor add-on repository** — added `repository.json` so HA recognizes the repo as a valid custom add-on store.
- Rewrote `config.json` to remove invalid keys (`build`, `host_network`) and corrected the `map` field format to the required string-list format (`["data:rw"]`).
- Added `build.json` so the Supervisor knows which HA Python base images to use when building for each arch.
- Updated `Dockerfile` to use the `ARG BUILD_FROM` pattern required by HA Supervisor builds.
- Simplified `hacs.json` to only contain valid HACS v2 fields (`name`, `homeassistant`, `iot_class`).
- Added `url` field to `config.json` and `repository.json` for proper linking in the UI.

## [0.1.1] - 2026-03-29
- Convert the repository into a valid Supervisor add-on by adding a root `config.json`, exposing official build metadata, and publishing a dedicated `Dockerfile`.
- Update HACS metadata so the integration registers under the `custom_components` root and point to the canonical GitHub repository.
- Make the integration auto-discover the add-on when Supervisor advertises the `ha_basic_addon` domain, simplifying setup.

## [0.1.0] - 2026-03-29
- Initial release of the HA Basic Add-on repository.
- Includes a lightweight HTTP health service in the add-on container and a companion integration that surfaces the add-on health check as a sensor.
