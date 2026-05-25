"""
Tum saldirilari sirayla calistir + cikisi terminal-style PNG olarak kaydet.

Her saldiriyi subprocess olarak baslatir, stdout+stderr'i toplar, PIL ile
amber-terminal goruntusunde renderlayip captures/ klasorune yazar.

Kullanim:
    python attacks/demo_all.py
    # captures/01_mitm.png, 02_rogue.png, 03_free.png, 04_dos.png, 05_fw.png
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "captures"
CAP.mkdir(parents=True, exist_ok=True)

# Renkler (mucahic.com amber-terminal palette)
BG = (10, 13, 10)
PANEL = (15, 19, 16)
LINE = (44, 48, 38)
AMBER = (212, 160, 71)
AMBER_BR = (244, 198, 110)
TXT = (210, 209, 196)
TXT_DIM = (135, 132, 116)
RED = (200, 80, 70)
GREEN = (120, 180, 100)


def font(size=14, bold=False):
    candidates = [
        "C:/Windows/Fonts/consola.ttf" if not bold else "C:/Windows/Fonts/consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def render_terminal(lines: list[str], title: str, out: Path, width=1280, height=720):
    """Verilen log satirlarini amber-terminal goruntusu olarak PNG'e yaz."""
    im = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(im)

    # Header bar
    d.rectangle([0, 0, width, 38], fill=PANEL)
    d.line([0, 38, width, 38], fill=LINE)
    f_title = font(13, bold=True)
    f_sub = font(11)
    d.text((20, 12), title, fill=AMBER, font=f_title)
    d.text((width - 240, 14), "// MUCAHIC LAB // dossier-10", fill=TXT_DIM, font=f_sub)

    # Body
    f_mono = font(13)
    line_h = 18
    y = 56
    max_lines = (height - 80) // line_h
    show = lines[-max_lines:] if len(lines) > max_lines else lines
    for ln in show:
        color = TXT
        if "[mitm]" in ln or "[rogue]" in ln or "[fw]" in ln or "[dos]" in ln:
            color = AMBER_BR
        if "HARVEST" in ln or "REWRITE" in ln or "ENJEKSIYON" in ln or "LURE" in ln:
            color = RED
        if "Accepted" in ln or "BASLIYOR" in ln:
            color = GREEN
        if "->" in ln or "<-" in ln:
            color = TXT
        if ln.startswith("##"):
            color = AMBER
        # Truncate uzun satirlari
        if len(ln) > 145:
            ln = ln[:142] + "..."
        d.text((24, y), ln, fill=color, font=f_mono)
        y += line_h

    im.save(out, "PNG", optimize=True)
    print(f"   [demo_all] wrote {out.name}")


def run_capture(cmd: list[str], duration_s: int, title: str) -> list[str]:
    """Subprocess'i baslat, duration_s saniye topla, sonra durdur. stdout+stderr karisik liste doner."""
    print(f"\n## {title}")
    print(f"   $ {' '.join(cmd)}")
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    out = []
    start = time.time()
    try:
        while time.time() - start < duration_s:
            line = p.stdout.readline()
            if line == "" and p.poll() is not None:
                break
            if line:
                out.append(line.rstrip())
                print("   |", line.rstrip())
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
    return out


def attack_dos():
    """DoS dogrudan SteVe'e baglandigi icin tek script yeter."""
    lines = run_capture(
        [sys.executable, "attacks/dos_flood.py", "--concurrency", "30", "--duration", "10"],
        duration_s=14, title="04 // DOS FLOOD (30 bot * 10s)",
    )
    render_terminal(lines, "04 // DOS FLOOD", CAP / "04_dos.png")


def attack_rogue():
    """Sahte CSMS sunucu + EVSE'yi bagla, harvest yapilir + UpdateFirmware enjekte."""
    rogue = subprocess.Popen(
        [sys.executable, "attacks/rogue_csms.py", "--port", "8500"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    time.sleep(2)
    print("\n## 02 // ROGUE CSMS (sunucu acildi :8500)")
    evse_lines = run_capture(
        [sys.executable, "evse-sim/charge_point.py",
         "--csms", "ws://localhost:8500/CentralSystemService",
         "--cp-id", "EVSE-ROGUE-001", "--auto-charge", "--id-tag", "REAL-USER-CARD-42", "--duration", "10"],
        duration_s=15, title="02 // EVSE -> ROGUE CSMS",
    )
    # Rogue CSMS log'lari topla
    rogue.terminate()
    try:
        rogue_out, _ = rogue.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        rogue.kill()
        rogue_out = ""
    rogue_lines = (rogue_out or "").splitlines()
    combined = ["## ROGUE CSMS LOG"] + rogue_lines + ["", "## EVSE LOG"] + evse_lines
    render_terminal(combined, "02 // ROGUE CSMS + EVSE", CAP / "02_rogue.png")


def attack_firmware():
    """firmware_inject.py + bir EVSE baglat, EVSE UpdateFirmware aliyor."""
    fw = subprocess.Popen(
        [sys.executable, "attacks/firmware_inject.py", "--port", "8600"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    time.sleep(2)
    evse_lines = run_capture(
        [sys.executable, "evse-sim/charge_point.py",
         "--csms", "ws://localhost:8600/CentralSystemService",
         "--cp-id", "EVSE-INJECT-001"],
        duration_s=8, title="05 // FIRMWARE INJECTION",
    )
    fw.terminate()
    try:
        fw_out, _ = fw.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        fw.kill()
        fw_out = ""
    combined = ["## ROGUE CSMS"] + (fw_out or "").splitlines() + ["", "## EVSE"] + evse_lines
    render_terminal(combined, "05 // FIRMWARE INJECTION", CAP / "05_fw.png")


def attack_mitm():
    """mitmproxy'yi baslat, sonra EVSE'yi proxy uzerinden bagla. Authorize idTag canli degisir.

    NOT: mitmproxy WebSocket'i proxy moduna alip OCPP icin uygun olmasi icin
    --mode reverse:ws://localhost:8180 ile calismasi gerek. Eger mitmdump
    PATH'te degilse, sadece dokumante eden bir SS uretiriz.
    """
    mitm = subprocess.Popen(
        ["mitmdump", "--mode", "reverse:http://localhost:8180", "-p", "8400",
         "-s", "attacks/ocpp_mitm.py", "--set", "termlog_verbosity=warn"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    time.sleep(3)
    print("\n## 01 // OCPP MITM (mitmdump :8400 -> SteVe :8180)")
    evse_lines = run_capture(
        [sys.executable, "evse-sim/charge_point.py",
         "--csms", "ws://localhost:8400/steve/websocket/CentralSystemService",
         "--cp-id", "EVSE-MITM-001", "--auto-charge", "--id-tag", "VICTIM-CARD-7", "--duration", "12"],
        duration_s=18, title="01 // EVSE through MITM",
    )
    mitm.terminate()
    try:
        mitm_out, _ = mitm.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        mitm.kill()
        mitm_out = ""
    combined = ["## MITMPROXY LOG"] + (mitm_out or "").splitlines()[:30] + ["", "## EVSE LOG"] + evse_lines
    render_terminal(combined, "01 // OCPP MITM", CAP / "01_mitm.png")


def attack_free_charge():
    """free_charge.py mitm uzerinden MeterValues sifirlama."""
    mitm = subprocess.Popen(
        ["mitmdump", "--mode", "reverse:http://localhost:8180", "-p", "8401",
         "-s", "attacks/free_charge.py", "--set", "termlog_verbosity=warn"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    time.sleep(3)
    evse_lines = run_capture(
        [sys.executable, "evse-sim/charge_point.py",
         "--csms", "ws://localhost:8401/steve/websocket/CentralSystemService",
         "--cp-id", "EVSE-FREE-001", "--auto-charge", "--id-tag", "DEMO-TAG-1", "--duration", "20"],
        duration_s=26, title="03 // FREE CHARGE",
    )
    mitm.terminate()
    try:
        mitm_out, _ = mitm.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        mitm.kill()
        mitm_out = ""
    combined = ["## MITMPROXY LOG"] + (mitm_out or "").splitlines()[:40] + ["", "## EVSE LOG"] + evse_lines
    render_terminal(combined, "03 // FREE CHARGE", CAP / "03_free.png")


def main():
    print("== DEMO_ALL: 5 saldiri sirayla ==")
    # MitM + free charge SteVe'e bagimli; rogue/firmware bagimsiz
    # Once SteVe'e bagli olanlar (CSMS calisiyor olmali)
    attack_mitm()
    attack_free_charge()
    attack_dos()
    # Bagimsiz olanlar (kendi sahte CSMS'leri var)
    attack_rogue()
    attack_firmware()
    print("\n== TAMAM. captures/ klasorune bak. ==")


if __name__ == "__main__":
    main()
