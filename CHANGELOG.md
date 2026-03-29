# Changelog

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
