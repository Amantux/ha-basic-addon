# HA Basic Add-on

A minimal but **fully working** Home Assistant add-on + companion custom integration.
Demonstrates the complete Supervisor discovery chain — from a containerised HTTP service
through to auto-discovered sensor entities in Devices & Services.

---

## Add to Home Assistant

### Step 1 — Add the Supervisor repository

[![Add repository to Home Assistant Supervisor](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FAmantux%2Fha-basic-addon)

Or manually: **Settings → Add-ons → Add-on Store → ⋮ → Repositories** → paste `https://github.com/Amantux/ha-basic-addon`

### Step 2 — Add the integration via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Amantux&repository=ha-basic-addon&category=integration)

Or manually in HACS: **Integrations → ⋮ → Custom repositories** → paste `https://github.com/Amantux/ha-basic-addon` → category **Integration** → **Add**.

### Step 3 — Start the add-on, watch it appear automatically

Install **HA Basic Add-on** from the add-on store, then **Start** it.
Within seconds a **New device found** card will appear in
**Settings → Devices & Services** — no manual configuration needed.

[![Start setting up HA Basic Add-on integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=ha_basic_addon)

---

## How it works

### The discovery chain (end to end)

```
┌─────────────────────────────────────────────────────────────────┐
│  Supervisor host                                                 │
│                                                                  │
│  ┌─────────────────────────┐      ┌──────────────────────────┐  │
│  │  HA Basic Add-on        │      │  Home Assistant core     │  │
│  │  (Docker container)     │      │                          │  │
│  │                         │  1   │                          │  │
│  │  main.py starts         │─────▶│  Supervisor /discovery   │  │
│  │  register_discovery()   │  POST│  validates service name  │  │
│  │                         │      │  assigns UUID            │  │
│  │  ThreadingHTTPServer    │      │         │                │  │
│  │  0.0.0.0:8080           │      │         │ 2              │  │
│  │                         │      │         ▼                │  │
│  │  GET /health            │◀─────│  async_step_hassio()     │  │
│  │  → {"status":"ok", ...} │  3   │  set_unique_id(uuid)     │  │
│  │                         │      │  validate /health  ──────│──┘
│  └─────────────────────────┘      │         │ passes         │
│                                   │         ▼ 4              │
│                                   │  async_step_hassio_       │
│                                   │    confirm()             │
│                                   │  _set_confirm_only()     │
│                                   │  → "New device found"    │
│                                   │     badge in UI          │
│                                   │         │ 5 user clicks  │
│                                   │         ▼                │
│                                   │  async_create_entry()    │
│                                   │  coordinator polls       │
│                                   │  /health every 60 s      │
└───────────────────────────────────┴──────────────────────────┘
```

### Why each step is necessary

| Step | What happens | Why it matters |
|------|-------------|----------------|
| **1** | `main.py` calls `POST http://supervisor/discovery` on startup | `"discovery": ["ha_basic_addon"]` in `config.json` is only an *allowlist* — the add-on must make the actual call. Without it Supervisor never notifies HA and the flow never starts. |
| **2** | Supervisor forwards `HassioServiceInfo(uuid, config)` to HA | Supervisor sets `context={"source": SOURCE_HASSIO}` → HA maps this to `async_step_hassio` (not `async_step_discovery`, which is for mDNS/DHCP). |
| **3** | `async_step_hassio` validates the `/health` endpoint | Fail fast before showing any UI. Aborts cleanly if the add-on isn't ready. |
| **4** | `async_step_hassio_confirm` calls `_set_confirm_only()` | This single call surfaces the **"New device found"** notification badge. Without it the flow runs silently and the user never sees the card. |
| **5** | User clicks Submit; entry is created | `translations/en.json` (not `strings.json`) provides the runtime UI strings HA renders in the form. |

### Why `translations/en.json` is required

`strings.json` is a *build-time source file* used by HA's internal translation toolchain.
Custom components must ship `translations/en.json` themselves — that is what HA reads at
runtime to render config flow forms. Without it, step labels show as raw keys like
`config.step.hassio_confirm.description`.

---

## Entities

Once the integration is set up, two sensor entities appear under a single **HA Basic Add-on** device card:

| Entity | Type | State | Extra attributes |
|--------|------|-------|-----------------|
| `sensor.*_status` | Text | `ok` (or error string) | `greeting`, `path`, `timestamp` |
| `sensor.*_uptime` | Duration (seconds) | e.g. `142.3` | — |

`sensor.*_uptime` is typed as `SensorDeviceClass.DURATION` / `SensorStateClass.TOTAL_INCREASING`
so Home Assistant can graph it over time.

---

## Options

After setup, go to **Settings → Devices & Services → HA Basic Add-on → Configure** to adjust:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| Poll interval | 60 s | 10 – 3600 s | How often HA fetches the `/health` endpoint |

---

## Repository structure

```
ha-basic-addon/
├── config.json                        # Supervisor add-on manifest
├── build.json                         # HA base image references per arch
├── Dockerfile                         # Add-on container (uses ARG BUILD_FROM)
├── repository.json                    # Supervisor repository metadata
├── hacs.json                          # HACS integration metadata
│
├── addon/
│   ├── main.py                        # HTTP service + Supervisor discovery registration
│   └── run.sh                         # Entrypoint: python3 main.py
│
└── custom_components/ha_basic_addon/
    ├── manifest.json                  # Integration metadata (must stay in version sync with config.json)
    ├── __init__.py                    # async_setup_entry, async_unload_entry
    ├── config_flow.py                 # async_step_hassio → async_step_hassio_confirm → create_entry
    ├── coordinator.py                 # DataUpdateCoordinator, polls /health
    ├── sensor.py                      # HaBasicAddonStatusSensor, HaBasicAddonUptimeSensor
    ├── const.py                       # DOMAIN, CONF_*, DEFAULT_*
    ├── helpers.py                     # build_health_url()
    ├── strings.json                   # Build-time translation source
    └── translations/
        └── en.json                    # Runtime UI strings (required by HA)
```

---

## Development

**Bump the version on every push** — both `config.json` and `manifest.json` must match,
and a GitHub Release must exist for HACS to deliver updates.

```bash
# 1. Edit config.json  "version": "x.y.z"
# 2. Edit custom_components/ha_basic_addon/manifest.json  "version": "x.y.z"
# 3. Add CHANGELOG.md entry
# 4. git commit && git push
# GitHub Actions (.github/workflows/validate.yml) will:
#   - Fail the build if versions are out of sync
#   - Auto-create a GitHub Release so HACS can deliver the update
```

**Test the health endpoint locally:**

```bash
python3 addon/main.py
# In another terminal:
curl http://127.0.0.1:8080/health
# {"status": "ok", "uptime": 1.23, "greeting": "Hello from HA Basic Add-on!", ...}
```

---

## CHANGELOG

See [CHANGELOG.md](CHANGELOG.md) for full version history.
