# Changelog

## [0.1.1] - 2026-03-29
- Convert the repository into a valid Supervisor add-on by adding a root `config.json`, exposing official build metadata, and publishing a dedicated `Dockerfile`.
- Update HACS metadata so the integration registers under the `custom_components` root and point to the canonical GitHub repository.
- Make the integration auto-discover the add-on when Supervisor advertises the `ha_basic_addon` domain, simplifying setup.

## [0.1.0] - 2026-03-29
- Initial release of the HA Basic Add-on repository.
- Includes a lightweight HTTP health service in the add-on container and a companion integration that surfaces the add-on health check as a sensor.
