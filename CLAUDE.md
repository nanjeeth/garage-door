# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

Self-hosted garage door controller. An **ESP32** reads the door's open/closed
state with an ultrasonic distance sensor and pulses a relay to operate the
opener. A **FastAPI** backend brokers between the device and clients, stores
state/events, and sends notifications. A **React** web app is the UI. The stack
runs on a home server via Docker Compose, with remote access over Tailscale.

Data flow: `ESP32  ⇄  FastAPI backend  ⇄  React frontend`
- Backend → ESP32: polls `GET /status` and sends `POST /trigger` (bearer auth).
- ESP32 → backend: `POST /api/door/webhook` on every confirmed state change.

## Layout

- `esp32/garage_door/` — ESP32 (Arduino) firmware.
  - `garage_door.ino` — **gitignored**; contains real WiFi creds + auth token.
  - `garage_door.ino.example` — sanitized, **tracked** template. **Mirror every
    firmware change into this file.**
- `backend/` — FastAPI app (port **8002**).
  - `app/main.py` — app entry; mounts the door router at `/api/door`, starts the
    scheduler in the lifespan, `/api/health` healthcheck.
  - `app/routers/door.py` — endpoints: `status`, `trigger`, `events`,
    `auto-open/{enabled}`, `webhook`.
  - `app/esp32_client.py` — HTTP client to the ESP32 (`ESP32_IP`, `ESP32_TOKEN`).
  - `app/scheduler.py` — background tasks: poll ESP32 every 5s, phone-arrival
    auto-open, door-open-too-long alert; owns door-state bookkeeping.
  - `app/models.py` / `app/database.py` — SQLAlchemy `DoorState` & `DoorEvent`,
    SQLite.
  - `app/notifier.py` — Telegram notifications (gated by `NOTIFY_ENABLED`).
  - `app/phone_detector.py` — phone-on-network detection for auto-open.
  - `app/config.py` — all config via env vars.
  - `run.py` — local dev runner (uvicorn, reload).
- `frontend/` — React 19 + Vite + TypeScript, served by nginx (port **3001**).
  - `nginx.conf` — serves the SPA and proxies `/api/` → `backend:8002`.
  - `src/api.ts` — API client; uses **relative URLs in prod**, `localhost:8002`
    in dev.
  - `src/components/Dashboard.tsx` — main UI (status badge, trigger button,
    event list). The "● Online/Offline" badge reflects `esp32_reachable`.
- `docker-compose.yml` — runs `backend` + `frontend`.

## Running / building

- **Full stack:** `docker compose up -d --build` → backend `:8002`, frontend
  `:3001`. The frontend proxies `/api/` to the backend, so use the frontend URL.
- **Backend dev:** `cd backend && python run.py` (uvicorn on `0.0.0.0:8002`,
  hot reload).
- **Frontend dev:** `cd frontend && npm install && npm run dev`. In dev,
  `api.ts` targets `http://localhost:8002`.
- **Firmware:** open `esp32/garage_door/garage_door.ino` in Arduino IDE, board
  **"ESP32 Dev Module"**, install the **ArduinoJson** library, Upload. Serial
  monitor at **115200**.

## Firmware notes (`garage_door.ino`)

- **Hardware:** HC-SR04**P** ultrasonic sensor — `TRIG=GPIO27`, `ECHO=GPIO14`,
  powered at **3.3V so no voltage divider is needed**. Relay `IN=GPIO26`,
  status LED `GPIO2`.
- **Relay is ACTIVE-HIGH** (`RELAY_ACTIVE_LOW = false`): idle `LOW` = released,
  `HIGH` = pressed. `/trigger` pulses 500ms. Idle level is set before enabling
  the output to avoid a boot-time phantom press.
- **Door state from distance:** OPEN when the reading falls inside a distance
  **window** `[OPEN_MIN_CM, OPEN_MAX_CM]` (35–85cm) around the open panel's
  distance (≈66cm). A parked car's roof (≈100cm), the empty floor (≈155cm), and
  no-echo all read farther and count as CLOSED. Using a window (not a single
  threshold) lets the sensor sit over the parking spot without confusing a
  present car for an open door — set `OPEN_MAX_CM` below the parked car's roof
  distance.
- **`CONFIRM_SAMPLES`** consecutive consistent readings are required before the
  state changes — rejects stray echoes that otherwise spam notifications.
- **Sensor aiming:** aim it where the open door panel parks within its beam.
  Thanks to the OPEN window it can sit over the parking spot — just keep
  `OPEN_MAX_CM` below the parked car's roof distance so a present car reads
  CLOSED.
- **WiFi resilience:** `setSleep(false)` keeps the radio responsive;
  `setAutoReconnect(true)` + `ensureWiFi()` (checked every 10s in `loop()`)
  rejoin automatically after a router reboot / WiFi drop.
- `DEBUG_DISTANCE` prints the live distance once/second over Serial for
  calibration; set `false` for a quiet build.

## Deployment / network

- Runs on the home server **np301813** (Ubuntu) via Docker Compose.
- **Fixed IPs via DHCP reservation** (so they don't drift after a router reboot):
  server → **192.168.1.141**, ESP32 → **192.168.1.160**. The backend's
  `ESP32_IP` and the firmware's hardcoded webhook `SERVER_URL` both depend on
  these. If either device changes IP, those configs break.
- **Remote access via Tailscale** (private tailnet). Do **NOT** use Tailscale
  Funnel — the app has no authentication.

## Conventions / gotchas

- **No authentication on the app** — it relies on network-level trust. Keep it
  off the public internet; only share over the private tailnet.
- **Secrets:** real WiFi creds + token live only in the gitignored
  `garage_door.ino` and the server's `.env`. Never commit them. Always mirror
  firmware logic changes into `garage_door.ino.example` with placeholders.
- The ESP32 must stay on the LAN to reach the opener; the server relays to it,
  so remote clients never talk to the ESP32 directly.
