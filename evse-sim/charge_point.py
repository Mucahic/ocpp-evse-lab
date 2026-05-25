"""
EVSE simulator (OCPP 1.6J client).

Mobility House Python ocpp kutuphanesi uzerinde, bir gercek charge point'in
CSMS ile yapacagi mesaj akisini taklit eder:

    [evse] ws connect /steve/websocket/CentralSystemService/<cp-id>
    [evse] BootNotification        -> RegistrationStatus.Accepted bekler
    [evse] StatusNotification(Available)
    [evse] Heartbeat (periyodik, 30s)
    [evse] Authorize(idTag=...)
    [evse] StartTransaction(...)
    [evse] MeterValues (5s'de bir)
    [evse] StopTransaction(...)

Kullanim:
    python evse-sim/charge_point.py --cp-id EVSE-001
    python evse-sim/charge_point.py --cp-id EVSE-001 --auto-charge --id-tag DEMO-TAG-1

CSMS uzerinden gelen RemoteStartTransaction / Reset / ChangeConfiguration / UpdateFirmware
cagrilarina da cevap verir, log'a dusurur.
"""
import argparse
import asyncio
import logging
from datetime import datetime, timezone

import websockets

from ocpp.routing import on
from ocpp.v16 import ChargePoint as Cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import (
    Action,
    AuthorizationStatus,
    ChargePointStatus,
    ChargePointErrorCode,
    RegistrationStatus,
    RemoteStartStopStatus,
    ResetStatus,
    ConfigurationStatus,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [evse] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("evse-sim")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ChargePoint(Cp):
    """OCPP 1.6 charge point implementasyonu. CSMS->CP yondeki cagrilara cevap verir."""

    def __init__(self, cp_id, connection):
        super().__init__(cp_id, connection)
        self.transaction_id = None
        self.meter_wh = 0  # Wh cinsinden sayac

    # ---------- CSMS -> CP yonu (CSMS'ten gelen istekler) ----------

    @on(Action.get_configuration)
    async def on_get_configuration(self, key=None, **kwargs):
        log.info("<- GetConfiguration key=%s", key)
        return call_result.GetConfiguration(
            configuration_key=[
                {"key": "HeartbeatInterval", "readonly": False, "value": "30"},
                {"key": "MeterValueSampleInterval", "readonly": False, "value": "5"},
                {"key": "NumberOfConnectors", "readonly": True, "value": "1"},
            ],
            unknown_key=[],
        )

    @on(Action.change_configuration)
    async def on_change_configuration(self, key, value, **kwargs):
        log.info("<- ChangeConfiguration %s=%s", key, value)
        return call_result.ChangeConfiguration(status=ConfigurationStatus.accepted)

    @on(Action.remote_start_transaction)
    async def on_remote_start_transaction(self, id_tag, connector_id=None, **kwargs):
        log.info("<- RemoteStartTransaction id_tag=%s connector=%s", id_tag, connector_id)
        # Gercek charge point bunu kabul edip arkadan StartTransaction tetikler.
        asyncio.create_task(self.run_charging_session(id_tag))
        return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.accepted)

    @on(Action.remote_stop_transaction)
    async def on_remote_stop_transaction(self, transaction_id, **kwargs):
        log.info("<- RemoteStopTransaction tx=%s", transaction_id)
        return call_result.RemoteStopTransaction(status=RemoteStartStopStatus.accepted)

    @on(Action.reset)
    async def on_reset(self, type, **kwargs):
        log.warning("<- Reset type=%s (yeniden baslama simulasyonu)", type)
        return call_result.Reset(status=ResetStatus.accepted)

    @on(Action.update_firmware)
    async def on_update_firmware(self, location, retrieve_date, **kwargs):
        log.error("<- UpdateFirmware ! location=%s retrieve_date=%s", location, retrieve_date)
        log.error("    NOT: bu URL'den firmware indirilip kuruluyor olsaydi, RCE vektoru burada.")
        return call_result.UpdateFirmware()

    # ---------- CP -> CSMS yonu (bizim disari attigimiz mesajlar) ----------

    async def send_boot(self):
        req = call.BootNotification(
            charge_point_model="MUCAHIC-EVSE-SIM",
            charge_point_vendor="MUCAHIC LAB",
            firmware_version="1.0.0",
        )
        log.info("-> BootNotification")
        resp = await self.call(req)
        log.info("   .status=%s interval=%s", resp.status, resp.interval)
        return resp

    async def send_status(self, status: ChargePointStatus):
        req = call.StatusNotification(
            connector_id=1,
            error_code=ChargePointErrorCode.no_error,
            status=status,
            timestamp=iso_now(),
        )
        log.info("-> StatusNotification %s", status)
        await self.call(req)

    async def send_heartbeat(self):
        log.info("-> Heartbeat")
        return await self.call(call.Heartbeat())

    async def send_authorize(self, id_tag: str):
        log.info("-> Authorize id_tag=%s", id_tag)
        resp = await self.call(call.Authorize(id_tag=id_tag))
        log.info("   .id_tag_info.status=%s", resp.id_tag_info["status"])
        return resp

    async def send_start_transaction(self, id_tag: str):
        req = call.StartTransaction(
            connector_id=1,
            id_tag=id_tag,
            meter_start=self.meter_wh,
            timestamp=iso_now(),
        )
        log.info("-> StartTransaction meter_start=%d Wh", self.meter_wh)
        resp = await self.call(req)
        self.transaction_id = resp.transaction_id
        log.info("   .transaction_id=%s status=%s", resp.transaction_id, resp.id_tag_info["status"])
        return resp

    async def send_meter_values(self, energy_wh: int, power_w: int):
        if self.transaction_id is None:
            return
        req = call.MeterValues(
            connector_id=1,
            transaction_id=self.transaction_id,
            meter_value=[{
                "timestamp": iso_now(),
                "sampled_value": [
                    {"value": str(energy_wh), "measurand": "Energy.Active.Import.Register", "unit": "Wh"},
                    {"value": str(power_w),   "measurand": "Power.Active.Import",            "unit": "W"},
                ],
            }],
        )
        log.info("-> MeterValues energy=%d Wh power=%d W", energy_wh, power_w)
        await self.call(req)

    async def send_stop_transaction(self, id_tag: str):
        req = call.StopTransaction(
            meter_stop=self.meter_wh,
            timestamp=iso_now(),
            transaction_id=self.transaction_id,
            reason="Local",
            id_tag=id_tag,
        )
        log.info("-> StopTransaction meter_stop=%d Wh", self.meter_wh)
        await self.call(req)
        self.transaction_id = None

    # ---------- ust seviye senaryolar ----------

    async def run_charging_session(self, id_tag: str, duration_s: int = 30, power_w: int = 7400):
        """Tam bir sarj seansi: authorize -> start -> meter values -> stop."""
        log.info("== SARJ SEANSI BASLIYOR id_tag=%s sure=%ss guc=%dW ==", id_tag, duration_s, power_w)
        auth = await self.send_authorize(id_tag)
        if auth.id_tag_info["status"] != AuthorizationStatus.accepted:
            log.warning("Authorize REDDEDILDI, seans iptal.")
            return
        await self.send_status(ChargePointStatus.preparing)
        await self.send_start_transaction(id_tag)
        await self.send_status(ChargePointStatus.charging)
        step_s = 5
        for _ in range(duration_s // step_s):
            await asyncio.sleep(step_s)
            self.meter_wh += int(power_w * step_s / 3600)
            await self.send_meter_values(self.meter_wh, power_w)
        await self.send_status(ChargePointStatus.finishing)
        await self.send_stop_transaction(id_tag)
        await self.send_status(ChargePointStatus.available)
        log.info("== SARJ SEANSI BITTI ==")

    async def heartbeat_loop(self, interval_s: int = 30):
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self.send_heartbeat()
            except Exception as e:
                log.error("Heartbeat fail: %s", e)
                return


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csms", default="ws://localhost:8180/steve/websocket/CentralSystemService")
    ap.add_argument("--cp-id", default="EVSE-001", help="OCPP charge box id")
    ap.add_argument("--id-tag", default="DEMO-TAG-1", help="kullanilacak RFID idTag")
    ap.add_argument("--auto-charge", action="store_true", help="boot sonrasi otomatik sarj seansi tetikle")
    ap.add_argument("--duration", type=int, default=30, help="otomatik sarj seansinin saniye cinsinden suresi")
    args = ap.parse_args()

    url = f"{args.csms.rstrip('/')}/{args.cp_id}"
    log.info("connecting -> %s", url)

    async with websockets.connect(url, subprotocols=["ocpp1.6"]) as ws:
        cp = ChargePoint(args.cp_id, ws)
        boot_task = asyncio.create_task(cp.send_boot())
        listen_task = asyncio.create_task(cp.start())
        boot_resp = await boot_task
        if boot_resp.status != RegistrationStatus.accepted:
            log.error("CSMS bizi kabul etmedi (%s), cikiliyor.", boot_resp.status)
            return
        await cp.send_status(ChargePointStatus.available)
        hb_task = asyncio.create_task(cp.heartbeat_loop(boot_resp.interval or 30))
        if args.auto_charge:
            asyncio.create_task(cp.run_charging_session(args.id_tag, duration_s=args.duration))
        await listen_task
        hb_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Kapaniyor.")
