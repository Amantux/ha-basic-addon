# ha-basic-addon

This repository provides a minimal Home Assistant add-on **plus** a companion custom integration. It is designed to demonstrate a basic containerized service that the integration can consume and to show how an add-on and a HACS-installable integration can work together end to end.

## Components

1. **Add-on (`addon/`)** – runs a tiny HTTP service (`main.py`) that exposes a `/health` endpoint and echoes configuration values. It ships with a simple Dockerfile and Supervisor metadata so it can be installed as a Hass.io add-on.
2. **Integration (`custom_components/ha_basic_addon`)** – a custom integration that discovers the add-on, allows configuration through a config flow, and exposes a sensor that polls the add-on health endpoint.

## Quick setup

1. **Install the add-on**
   - Go to Hass.io Supervisor → Add-on Store → *Repositories* and add `https://github.com/Amantux/ha-basic-addon`.
   - Install **HA Basic Add-on**, then configure any options you need (host/port/greeting) and start it.
   - The add-on ships with a `config.json` at the repository root so Supervisor recognizes it automatically.

2. **Install the integration via HACS**
   - In HACS go to **Integrations → Custom repositories** and register this repository with category **Integration**.
   - Install the integration, then restart Home Assistant to make it available.

3. **Let Home Assistant discover the add-on**
   - When the add-on runs, Supervisor sends discovery information for the `ha_basic_addon` domain.
   - A prompt appears in Settings → Devices & Services to finish setting up the `Basic Add-on Health` sensor.

## Development notes

- Modify `addon/main.py` to expose additional actions, endpoints, or metadata for the integration.
- The integration uses a `DataUpdateCoordinator` to poll `/health` once every 60 seconds and surface JSON fields as device state attributes.
- Update `CHANGELOG.md` when you ship new versions or change the discovery workflow.
