# OCPP 1.6J EVSE Attack Lab

Pure-software lab that wires a real OCPP 1.6J Central System (SteVe) to a
scriptable Python EVSE (charge point) and a mitmproxy WebSocket interceptor.
Every attack runs end-to-end over real OCPP-J traffic, no physical charger
required.

Companion write-up: [EV Şarj İstasyonları: OCPP'nin İçine Girmek](https://mucahic.com/dossier-10.html)

## Components

```
lab/dossier-10/
  docker-compose.yml   MariaDB + SteVe CSMS (OCPP 1.6J central system)
  evse-sim/            Python EVSE client (mobility-house `ocpp` lib)
  attacks/             5 attack scripts + demo orchestrator
  scripts/             setup / up / down helpers
  diagrams/            article image generators
  captures/            runtime artifacts (gitignored)
  external/            SteVe source, cloned by setup (gitignored)
```

## Stack

| Piece     | What                                                          |
| --------- | ------------------------------------------------------------- |
| SteVe     | Open-source OCPP 1.6J Central System (CSMS), `steve-3.7.1`    |
| MariaDB   | SteVe backing store                                           |
| EVSE sim  | Python charge point on the mobility-house `ocpp` library      |
| mitmproxy | WebSocket man-in-the-middle for the live-rewrite attacks      |

- OCPP-J endpoint: `ws://localhost:8180/steve/websocket/CentralSystemService/<chargeBoxId>`
- SteVe manager: `http://localhost:8180/manager/home` (`admin` / `1234`)

## Attacks

| # | Script               | Technique                                                    |
|---|----------------------|--------------------------------------------------------------|
| 1 | `ocpp_mitm.py`       | MitM Authorize `idTag` rewrite (mitmproxy WS addon)          |
| 2 | `rogue_csms.py`      | Rogue Central System via hijacked DNS/config, harvests data  |
| 3 | `free_charge.py`     | MeterValues / `meterStop` zeroing, "free" energy             |
| 4 | `dos_flood.py`       | Parallel fake charge-box BootNotification + Heartbeat storm  |
| 5 | `firmware_inject.py` | Attacker-side `UpdateFirmware` injection                     |
|   | `demo_all.py`        | Runs every attack, renders amber-terminal PNGs to captures/  |

## Requirements

- Docker + Docker Compose
- Python 3.10+ with: `pip install ocpp websockets mitmproxy Pillow`

## Run

```
python scripts/setup.py                          # clone SteVe + docker compose build
python scripts/up.py                             # start MariaDB + SteVe, wait for health
python evse-sim/charge_point.py --auto-charge    # baseline session (cp-id EVSE-001)
```

Then run an attack, e.g. the rogue CSMS and point the EVSE at it:

```
python attacks/rogue_csms.py --port 8500 --harvest captures/harvested.json
python evse-sim/charge_point.py --csms ws://localhost:8500 --auto-charge
python attacks/demo_all.py                       # full sequence + screenshots
```

Tear down:

```
python scripts/down.py
```

## Disclaimer

Lab-only. Every component runs on localhost against a simulated charger and a
disposable SteVe instance. Do not point these scripts at charging
infrastructure you do not own.
