"""
dossier-10 yazisinin gorsellerini uretir:
  - cover.jpg              ana kapak (1600x600), EV fis + glitch + ocpp temasi
  - ocpp_stack.png         OCPP-J 1.6 protokol katmanlari
  - attack_surface.png     EVSE / CSMS / Attacker akis diyagrami
  - mitm_flow.png          OCPP Authorize akisinda MitM noktasi

Tum cikis dosyalari ../../images/dossier-10/ klasorune gider.
"""
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).resolve().parents[3] / "images" / "dossier-10"
OUT.mkdir(parents=True, exist_ok=True)

# Site palette
BG = (10, 13, 10)
PANEL = (15, 19, 16)
PANEL2 = (22, 26, 22)
LINE = (44, 48, 38)
LINE_BR = (70, 75, 60)
AMBER = (212, 160, 71)
AMBER_BR = (244, 198, 110)
AMBER_DIM = (140, 105, 50)
TXT = (210, 209, 196)
TXT_DIM = (135, 132, 116)
RED = (200, 80, 70)
GREEN = (120, 180, 100)
BLUE = (90, 140, 200)


def font(size=14, bold=False):
    candidates = [
        f"C:/Windows/Fonts/{'consolab' if bold else 'consola'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if bold else ''}.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


# -------------------------------------------------------------------- COVER
def cover(path: Path):
    W, H = 1600, 600
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    # 1) arka plan grid
    for x in range(0, W, 32):
        d.line([(x, 0), (x, H)], fill=(15, 20, 16), width=1)
    for y in range(0, H, 32):
        d.line([(0, y), (W, y)], fill=(15, 20, 16), width=1)

    # 2) sol panel: dev EV fis sembolu (CCS Type 2 - basitlestirilmis)
    fx, fy = 280, 300
    # Disinda yuvarlak govde
    d.ellipse([fx - 180, fy - 180, fx + 180, fy + 180], outline=AMBER, width=3)
    d.ellipse([fx - 170, fy - 170, fx + 170, fy + 170], outline=AMBER_DIM, width=1)
    # Type 2 ust kismi (5 pin)
    pins = [
        (fx - 70, fy - 90, 22),    # L1
        (fx + 70, fy - 90, 22),    # L2
        (fx - 40, fy - 20, 22),    # L3
        (fx + 40, fy - 20, 22),    # N
        (fx, fy + 50, 22),         # PE
    ]
    for px, py, r in pins:
        d.ellipse([px - r, py - r, px + r, py + r], outline=AMBER_BR, width=2)
        d.ellipse([px - r + 6, py - r + 6, px + r - 6, py + r - 6], fill=AMBER_DIM)
    # Alt DC pinler (CCS)
    d.ellipse([fx - 90, fy + 120, fx - 50, fy + 160], outline=AMBER_BR, width=2)
    d.ellipse([fx + 50, fy + 120, fx + 90, fy + 160], outline=AMBER_BR, width=2)

    # Glitch shift band
    band_y = random.randint(100, 500)
    crop = im.crop((0, band_y, W, band_y + 18))
    im.paste(crop, (random.randint(-30, 30), band_y))

    # 3) sag panel: OCPP mesaji JSON snippet
    panel_x = 750
    panel_y = 80
    d.rectangle([panel_x, panel_y, W - 60, H - 80], outline=LINE_BR, width=1)
    d.rectangle([panel_x, panel_y, panel_x + 320, panel_y + 30], fill=PANEL2)
    f_h = font(13, bold=True)
    f_m = font(15)
    f_xl = font(46, bold=True)
    f_l = font(28, bold=True)
    f_s = font(12)
    d.text((panel_x + 14, panel_y + 8), "// WIRE CAPTURE [Authorize]", fill=AMBER, font=f_h)

    lines = [
        '[ 2,',
        '  "9c3a-4b21-...",',
        '  "Authorize",',
        '  {',
        '    "idTag": "VICTIM-CARD-7"   <-- yakalandi',
        '  }',
        ']',
        '',
        '[ 2,',
        '  "9c3a-4b21-...",',
        '  "Authorize",',
        '  {',
        '    "idTag": "ATTACKER-CARD-1" <-- enjekte edildi',
        '  }',
        ']',
    ]
    yy = panel_y + 50
    for ln in lines:
        col = TXT
        if "yakalandi" in ln:
            col = AMBER_BR
        if "enjekte" in ln:
            col = RED
        d.text((panel_x + 22, yy), ln, fill=col, font=f_m)
        yy += 24

    # 4) baslik
    d.text((60, 30), "// DOSSIER-10", fill=AMBER, font=f_h)
    d.text((60, 55), "EV SARJ ISTASYONLARI: BOLUM 2", fill=TXT_DIM, font=f_s)

    # Vurgu baslik altta
    d.text((60, H - 130), "OCPP'NIN", fill=AMBER, font=f_xl)
    d.text((60, H - 80), "ICINE GIRMEK", fill=TXT, font=f_l)

    # Glitch noise
    for _ in range(40):
        xx = random.randint(0, W)
        yy = random.randint(0, H)
        d.line([(xx, yy), (xx + random.randint(3, 18), yy)], fill=AMBER_DIM, width=1)

    # Saglar
    im = im.filter(ImageFilter.SHARPEN)
    im.convert("RGB").save(path, "JPEG", quality=90)
    print(f"  -> {path.name}")


# -------------------------------------------------------------------- OCPP STACK
def ocpp_stack(path: Path):
    W, H = 1200, 600
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = font(15, bold=True)
    f_m = font(13)
    f_s = font(11)

    layers = [
        ("OCPP-J 1.6  // Action + Payload",            "Authorize, BootNotification, MeterValues, UpdateFirmware...", AMBER),
        ("MESSAGE FRAME [MsgType, UniqueId, Action, Payload]",  "[2, '9c3a-...', 'Authorize', { idTag: '...' }]",          AMBER_BR),
        ("JSON over WebSocket (RFC 6455)",             "Text frames, mostly UTF-8 JSON",                          TXT),
        ("WebSocket Upgrade",                          "GET /steve/websocket/.../EVSE-001  Upgrade: websocket",   TXT_DIM),
        ("TCP / TLS",                                  "TLS opsiyonel - profile-2 sertifika veya yok",            TXT_DIM),
        ("IP",                                         "Genelde 4G/Ethernet uzerinden mgmt VLAN",                  TXT_DIM),
    ]
    d.text((40, 24), "// OCPP-J 1.6 PROTOKOL KATMANLARI", fill=AMBER, font=f_h)

    box_w = W - 80
    box_h = 70
    yy = 80
    for title, sub, col in layers:
        d.rectangle([40, yy, 40 + box_w, yy + box_h], outline=col, width=1, fill=PANEL2)
        d.text((54, yy + 8), title, fill=col, font=f_h)
        d.text((54, yy + 32), sub, fill=TXT, font=f_m)
        yy += box_h + 10

    d.text((40, H - 30), "Saldirgan: en ust 2 katmani gormeyi sever. Ham JSON gorur, mesaj rewrite eder.", fill=AMBER_DIM, font=f_s)
    im.save(path, "PNG", optimize=True)
    print(f"  -> {path.name}")


# -------------------------------------------------------------------- ATTACK SURFACE
def attack_surface(path: Path):
    """3-satirli grid layout. Ust: ROGUE CSMS. Orta: EV-EVSE-MITM-CSMS. Alt: ATTACKER.
    Tum oklar orthogonal (right-angle), etiketler ok'larin tamamen disinda.
    """
    W, H = 1600, 880
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = font(17, bold=True)
    f_m = font(13)
    f_s = font(11)
    f_lbl = font(12, bold=True)

    # Baslik
    d.text((40, 28), "// EV SARJ EKOSISTEMI - SALDIRI YUZEYLERI", fill=AMBER, font=f_h)
    d.text((40, 52), "kirmizi yol = saldirgan kontrolu  /  amber yol = normal/mesru trafik", fill=TXT_DIM, font=f_s)

    # Grid alaninin koordinatlari
    # Sutun merkezleri (X)
    COL_EV    = 160
    COL_EVSE  = 540
    COL_MITM  = 920
    COL_CSMS  = 1300

    # Satir merkezleri (Y)
    ROW_TOP    = 180   # Rogue CSMS, Attacker (ust)
    ROW_MID    = 480   # Ana hat: EV, EVSE, MITM, CSMS
    ROW_BOT    = 760   # Attacker (alt)

    # Kutu olculeri
    BOX_W = 260
    BOX_H = 110

    def node(cx, cy, label, sub, color=AMBER, sublines=None):
        x1 = cx - BOX_W // 2
        y1 = cy - BOX_H // 2
        x2 = cx + BOX_W // 2
        y2 = cy + BOX_H // 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=2, fill=PANEL2)
        # icerde kucuk bir header bar
        d.rectangle([x1, y1, x2, y1 + 26], fill=PANEL)
        d.line([x1, y1 + 26, x2, y1 + 26], fill=color, width=1)
        d.text((x1 + 14, y1 + 6), label, fill=color, font=f_h)
        # alt aciklama satirlari
        lines = sublines or [sub]
        ty = y1 + 34
        for ln in lines:
            d.text((x1 + 14, ty), ln, fill=TXT, font=f_s)
            ty += 16
        return x1, y1, x2, y2

    # ---- Kutular ----
    # Orta satir
    ev_box   = node(COL_EV,   ROW_MID, "EV",   "",      AMBER,
                    sublines=["araba", "OBC + batarya"])
    evse_box = node(COL_EVSE, ROW_MID, "EVSE", "",      AMBER,
                    sublines=["sahadaki direk", "Linux + OCPP istemci"])
    mitm_box = node(COL_MITM, ROW_MID, "MITM", "",      RED,
                    sublines=["mitmproxy reverse", "WebSocket frame rewrite"])
    csms_box = node(COL_CSMS, ROW_MID, "CSMS", "",      GREEN,
                    sublines=["SteVe / MaEVe", "operatorun bulut tarafi"])

    # Ust: ROGUE CSMS (EVSE sutununun ustunde, biraz saga kaymis)
    rogue_box = node(COL_MITM, ROW_TOP, "ROGUE CSMS", "", RED,
                     sublines=["sahte sunucu", "ws://attacker.lab"])

    # Alt: ATTACKER (EV ile EVSE arasinda, alta)
    atk_box   = node(COL_EV + 160, ROW_BOT, "ATTACKER", "", RED,
                     sublines=["botnet / VPS", "100+ sahte EVSE bot"])

    # ---- Yardimcilar ----
    def hline(x1, x2, y, color, width=2):
        d.line([(x1, y), (x2, y)], fill=color, width=width)

    def vline(x, y1, y2, color, width=2):
        d.line([(x, y1), (x, y2)], fill=color, width=width)

    def head(x, y, direction, color, size=12):
        """Ok ucu, direction: 'right' 'left' 'up' 'down'."""
        if direction == "right":
            d.polygon([(x, y), (x - size, y - size//2), (x - size, y + size//2)], fill=color)
        elif direction == "left":
            d.polygon([(x, y), (x + size, y - size//2), (x + size, y + size//2)], fill=color)
        elif direction == "down":
            d.polygon([(x, y), (x - size//2, y - size), (x + size//2, y - size)], fill=color)
        elif direction == "up":
            d.polygon([(x, y), (x - size//2, y + size), (x + size//2, y + size)], fill=color)

    def label_box(x, y, text, color):
        """Yaziyi panel arka planli kucuk bir badge olarak goster, ok hatti uzerinde okunaklilik icin."""
        # text metric
        bbox = d.textbbox((0, 0), text, font=f_lbl)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 8, 4
        bx1 = x - pad_x
        by1 = y - pad_y
        bx2 = x + tw + pad_x
        by2 = y + th + pad_y
        d.rectangle([bx1, by1, bx2, by2], fill=BG, outline=color, width=1)
        d.text((x, y), text, fill=color, font=f_lbl)

    # ---- Oklar ----
    # 1) EV -> EVSE (amber, normal)
    y = ROW_MID
    x1 = ev_box[2]
    x2 = evse_box[0]
    hline(x1, x2 - 12, y, AMBER, width=2)
    head(x2 - 2, y, "right", AMBER)
    label_box((x1 + x2) // 2 - 70, y - 30, "ISO 15118 / CP-PWM", AMBER)

    # 2) EVSE -> CSMS (mesru OCPP yolu, ana hat, MITM uzerinden gitmiyor)
    # EVSE saginin altindan cikip MITM altindan asarak CSMS soluna gider.
    # Bunu MITM ust yoluna paralel ama uzakta cizecegim icin: ust koridordan gec.
    # Daha temiz: alttan, MITM altinda yatay cizgi.
    yy = ROW_MID + BOX_H // 2 + 50    # MITM kutusunun altinda
    # EVSE altindan baslat
    x_ev_bot  = COL_EVSE
    x_csms_bot = COL_CSMS
    # Dikey EVSE'den asagi
    vline(x_ev_bot, evse_box[3], yy, AMBER, width=2)
    hline(x_ev_bot, x_csms_bot, yy, AMBER, width=2)
    vline(x_csms_bot, yy, csms_box[3] + 1, AMBER, width=2)
    head(x_csms_bot, csms_box[3] + 2, "up", AMBER)
    label_box((x_ev_bot + x_csms_bot) // 2 - 56, yy - 28, "OCPP normal", AMBER)

    # 3) EVSE -> MITM -> CSMS (01, 03 - mitm yolu, ust yatay korridor)
    y_top = ROW_MID - BOX_H // 2 - 30  # MITM kutusunun ustunden gecmesin diye HEMEN UST
    # EVSE'den yukari cik
    x_ev = COL_EVSE
    x_mitm = COL_MITM
    x_csms = COL_CSMS
    # Bu yol ust koridordan gidiyor ama mantiken MITM kutusunun icine girip cikiyor demek istiyoruz.
    # Onun yerine: EVSE -> MITM dogrudan yatay (ROW_MID seviyesinde MITM solu) + MITM -> CSMS yatay
    # MITM kutusunda zaten orta satirda. EVSE sagi -> MITM solu yatay
    y_mid = ROW_MID
    x_evse_r = evse_box[2]
    x_mitm_l = mitm_box[0]
    # EVSE -> MITM yatay (ust koridor olmayacak, ortada zaten yer var)
    # Ama EV -> EVSE oku zaten orta seviyede, EVSE sagi ile MITM solu arasinda da yatay olabilir
    # Ust kismi rahatlatmak icin EVSE -> MITM'i sligh yuksege alalim
    y_mitm_path = y_mid - 8
    hline(x_evse_r, x_mitm_l - 12, y_mitm_path, RED, width=2)
    head(x_mitm_l - 2, y_mitm_path, "right", RED)
    label_box((x_evse_r + x_mitm_l) // 2 - 64, y_mitm_path - 28, "01,03 mitm", RED)

    # MITM -> CSMS yatay
    x_mitm_r = mitm_box[2]
    x_csms_l = csms_box[0]
    hline(x_mitm_r, x_csms_l - 12, y_mitm_path, RED, width=2)
    head(x_csms_l - 2, y_mitm_path, "right", RED)
    label_box((x_mitm_r + x_csms_l) // 2 - 74, y_mitm_path - 28, "rewrite gider", RED)

    # 4) EVSE -> ROGUE CSMS (02, 05) - sol-ust yonu, EVSE ustunden cik, ROGUE'a kadar
    x_ev_top = COL_EVSE
    y_ev_top = evse_box[1]
    # EVSE'den yukari ROW_TOP seviyesine kadar
    y_rogue_path = ROW_TOP
    # EVSE'nin ust orta noktasindan dik yukari, sonra saga ROGUE'a
    vline(x_ev_top, y_rogue_path + 8, y_ev_top - 2, RED, width=2)
    x_rogue_l = rogue_box[0]
    hline(x_ev_top, x_rogue_l - 12, y_rogue_path + 8, RED, width=2)
    head(x_rogue_l - 2, y_rogue_path + 8, "right", RED)
    label_box(x_ev_top + 50, y_rogue_path + 14, "02,05 DNS spoof / config", RED)

    # 5) ATTACKER -> CSMS (04 dos flood) - alttan saga uzun yatay + dikey
    x_atk_r = atk_box[2]
    y_atk = ROW_BOT
    y_path_bot = ROW_BOT + 0  # ATTACKER ile ayni seviye, dikey CSMS'e
    # ATTACKER sagindan saga uzun yatay
    hline(x_atk_r, csms_box[0] + (BOX_W // 4) , y_atk, RED, width=2)
    # Dikey yukari CSMS'e
    vline(csms_box[0] + (BOX_W // 4), y_atk, csms_box[3] + 1, RED, width=2)
    head(csms_box[0] + (BOX_W // 4), csms_box[3] + 2, "up", RED)
    label_box(x_atk_r + 40, y_atk - 28, "04 dos flood", RED)

    # ---- Lejand ----
    leg_y = H - 50
    d.rectangle([40, leg_y, 24 + 460, leg_y + 26], outline=LINE_BR, width=1, fill=PANEL)
    # amber sample
    d.line([(56, leg_y + 13), (96, leg_y + 13)], fill=AMBER, width=2)
    d.text((104, leg_y + 6), "normal trafik", fill=TXT, font=f_s)
    # red sample
    d.line([(232, leg_y + 13), (272, leg_y + 13)], fill=RED, width=2)
    d.text((280, leg_y + 6), "saldirgan kontrolundeki yol", fill=TXT, font=f_s)

    im.save(path, "PNG", optimize=True)
    print(f"  -> {path.name}")


# -------------------------------------------------------------------- MITM FLOW
def mitm_flow(path: Path):
    W, H = 1400, 600
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_h = font(15, bold=True)
    f_m = font(13)
    f_s = font(11)
    f_mono = font(12)

    d.text((40, 24), "// AUTHORIZE FLOW + MITM REWRITE", fill=AMBER, font=f_h)

    # Lifeline'lar
    cols = [
        (200, "EVSE", AMBER),
        (700, "MITM", RED),
        (1200, "CSMS", GREEN),
    ]
    for x, lbl, c in cols:
        d.rectangle([x - 70, 70, x + 70, 110], outline=c, width=2, fill=PANEL2)
        d.text((x - 30, 80), lbl, fill=c, font=f_h)
        # dikey cizgi
        for y in range(120, H - 40, 8):
            d.line([(x, y), (x, y + 4)], fill=LINE_BR, width=1)

    # Mesajlar
    msgs = [
        (150, 200, 700, "Authorize {idTag: 'VICTIM-CARD-7'}",      AMBER),
        (160, 700, 1200, "Authorize {idTag: 'ATTACKER-CARD-1'} **REWRITE**", RED),
        (220, 1200, 700, "AuthorizeResponse {status: Accepted, ...}", GREEN),
        (220, 700, 200, "AuthorizeResponse {status: Accepted, ...}", GREEN),
        (320, 200, 700, "StartTransaction {idTag: 'VICTIM-CARD-7', meterStart: 0}", AMBER),
        (320, 700, 1200, "StartTransaction {idTag: 'ATTACKER-CARD-1', meterStart: 0} **REWRITE**", RED),
        (380, 1200, 700, "StartTransactionResponse {transactionId: 17}", GREEN),
        (380, 700, 200, "StartTransactionResponse {transactionId: 17}", GREEN),
    ]
    for y, x1, x2, txt, col in msgs:
        d.line([(x1, y), (x2, y)], fill=col, width=2)
        ang = 0
        d.polygon([
            (x2, y),
            (x2 - 12 if x2 > x1 else x2 + 12, y - 6),
            (x2 - 12 if x2 > x1 else x2 + 12, y + 6),
        ], fill=col)
        # label
        lx = min(x1, x2) + 20
        d.text((lx, y - 22), txt, fill=col, font=f_mono)

    d.text((40, 460), "MITM 'Authorize' ve 'StartTransaction' cagrilarinin payload.idTag alanini canli olarak", fill=TXT, font=f_s)
    d.text((40, 478), "saldirgan idTag'ine yazar. CSMS log'unda ATTACKER-CARD-1 ile sarj gorulur.", fill=TXT, font=f_s)
    d.text((40, 500), "CSMS'ten gelen response'larda ise dokunulmaz. EVSE 'kabul edildim' der ve devam eder.", fill=TXT_DIM, font=f_s)

    im.save(path, "PNG", optimize=True)
    print(f"  -> {path.name}")


def main():
    print(f"Output -> {OUT}")
    cover(OUT / "cover.jpg")
    ocpp_stack(OUT / "ocpp_stack.png")
    attack_surface(OUT / "attack_surface.png")
    mitm_flow(OUT / "mitm_flow.png")
    print("Done.")


if __name__ == "__main__":
    main()
