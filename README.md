# ha-basic-addon

This repository provides a minimal Home Assistant add-on **plus** a companion custom integration. It is designed to demonstrate a basic containerized service that the integration can consume and to show how an add-on and a HACS-installable integration can work together end to end.

## Components

1. **Add-on (`addon/`)** – runs a tiny HTTP service (`main.py`) that exposes a `/health` endpoint and echoes configuration values. It ships with a simple Dockerfile and Supervisor metadata so it can be installed as a Hass.io add-on.
2. **Integration (`custom_components/ha_basic_addon`)** – a custom integration that discovers the add-on, allows configuration through a config flow, and exposes a sensor that polls the add-on health endpoint.

## Quick setup

1. **Add the Supervisor repository**
   - In Home Assistant go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories**.
   - Add `https://github.com/Amantux/ha-basic-addon` and click **Add**.
   - The **HA Basic Add-on** will appear in the store — install it, configure options if needed, and **Start** it.

2. **Install the integration via HACS**
   - In HACS go to **Integrations → ⋮ → Custom repositories**.
   - Paste `https://github.com/Amantux/ha-basic-addon`, select category **Integration**, and click **Add**.
   - Search for *HA Basic Add-on* in HACS, install it, and restart Home Assistant.

3. **Auto-discovery**
   - Once the add-on is running, Supervisor broadcasts a discovery event for the `ha_basic_addon` domain.
   - A card appears in **Settings → Devices & Services** — click **Configure** to finish setup.
   - A `Basic Add-on Health` sensor is created automatically.

## Development notes

- Modify `addon/main.py` to expose additional actions, endpoints, or metadata for the integration.
- The integration uses a `DataUpdateCoordinator` to poll `/health` once every 60 seconds and surface JSON fields as device state attributes.
- Update `CHANGELOG.md` when you ship new versions or change the discovery workflow.
