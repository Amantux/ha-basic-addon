# ha-basic-addon

This repository provides a minimal Home Assistant add-on **plus** a companion custom integration. It is designed to demonstrate a basic containerized service that the integration can consume and to show how an add-on and a HACS-installable integration can work together end to end.

## Components

1. **Add-on (`addon/`)** – runs a tiny HTTP service (`main.py`) that exposes a `/health` endpoint and echoes configuration values. It ships with a simple Dockerfile and Supervisor metadata so it can be installed as a Hass.io add-on.
2. **Integration (`custom_components/ha_basic_addon`)** – a custom integration that discovers the add-on, allows configuration through a config flow, and exposes a sensor that polls the add-on health endpoint.

## Quick setup

1. **Build & install the add-on**
   - Build the Docker image: `docker build -t ha-basic-addon addon/`
   - Push it to your registry (optional) and configure the supervisor add-on to use it.
   - In Supervisor, add this repository under **Add-on Store > Repositories**, install the add-on, and start it.

2. **Install the integration via HACS**
   - Add this repository under HACS (Custom repositories → Integration, category "Integration").
   - Search for *HA Basic Add-on* in HACS and install it.
   - Restart Home Assistant to load the new integration.

3. **Configure the integration**
   - In Home Assistant, go to **Settings > Devices & Services > Add Integration** and search for **HA Basic Add-on**.
   - Enter the add-on host (e.g., `http://127.0.0.1`) and port (defaults to `8080`).
   - A sensor named `Basic Add-on Health` will appear showing the response from `/health`.

## Development notes

- Modify `addon/main.py` to expose additional actions or data for the integration.
- The integration uses a `DataUpdateCoordinator` to poll `/health` once every 60 seconds.
- Update `CHANGELOG.md` when you ship new versions.
