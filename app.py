import os
import json
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")

# RSI — separate bot (falls back to the main bot / chat if not set)
RSI_BOT_TOKEN = os.environ.get("RSI_BOT_TOKEN") or BOT_TOKEN
RSI_CHAT_ID   = os.environ.get("RSI_CHAT_ID") or CHAT_ID

# Candle Detector — separate bot (falls back to the main bot / chat if not set)
CANDLE_BOT_TOKEN = os.environ.get("CANDLE_BOT_TOKEN") or BOT_TOKEN
CANDLE_CHAT_ID   = os.environ.get("CANDLE_CHAT_ID") or CHAT_ID

# Vol OB Precision Telegram Alert — separate bot (falls back to the main bot / chat if not set)
VOBTG_BOT_TOKEN = os.environ.get("VOBTG_BOT_TOKEN") or BOT_TOKEN
VOBTG_CHAT_ID   = os.environ.get("VOBTG_CHAT_ID") or CHAT_ID


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    import requests
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def send_telegram_rsi(text):
    url = f"https://api.telegram.org/bot{RSI_BOT_TOKEN}/sendMessage"
    import requests
    requests.post(url, json={"chat_id": RSI_CHAT_ID, "text": text}, timeout=10)


def send_telegram_candle(text):
    url = f"https://api.telegram.org/bot{CANDLE_BOT_TOKEN}/sendMessage"
    import requests
    requests.post(url, json={"chat_id": CANDLE_CHAT_ID, "text": text}, timeout=10)


def send_telegram_vobtg(text):
    url = f"https://api.telegram.org/bot{VOBTG_BOT_TOKEN}/sendMessage"
    import requests
    requests.post(url, json={"chat_id": VOBTG_CHAT_ID, "text": text}, timeout=10)


def fmt(v, dash="—"):
    """Telegram-safe value: never print None or an empty field."""
    return dash if v is None or v == "" else v


# ---------------------------------------------------------------
# VOL OB by Zonetraders W16 ALT — retracement alerts
# ---------------------------------------------------------------
def msg_volob_alt(d):
    side    = str(d.get("side", "")).upper()
    icon    = "🟢" if side == "BUY" else "🔴"
    n       = d.get("retracement")
    is_touch = d.get("mode") == "touch"
    label   = "AT ZONE" if is_touch else "APPROACHING"

    out = [
        f"{icon} <b>{fmt(side)} · {label}</b>  ·  retracement #{fmt(n)}",
        f"{fmt(d.get('sym'))}  |  TF: {fmt(d.get('tf'))}",
        f"Price: {fmt(d.get('price'))}",
        f"Zone: {fmt(d.get('zone_bot'))} – {fmt(d.get('zone_top'))}  ({fmt(d.get('zone_pct'))}%)",
    ]
    # distance only means something before price arrives
    if not is_touch:
        out.append(f"Distance: {fmt(d.get('distance'))}")
    return "\n".join(out)


# ---------------------------------------------------------------
# VOL OB — new zone / zone touch alerts
# ---------------------------------------------------------------
def msg_volob(d):
    side  = str(d.get("side", ""))
    icon  = "🟢" if side == "demand" else "🔴"
    event = d.get("event")
    head  = "new zone" if event == "new_ob" else "zone touched"
    out = [
        f"{icon} <b>{side.upper()}</b>  ·  {head}",
        f"{fmt(d.get('sym'))}  |  TF: {fmt(d.get('tf'))}",
    ]
    if d.get("price") is not None:
        out.append(f"Price: {fmt(d.get('price'))}")
    if d.get("bot") is not None:
        out.append(f"Zone: {fmt(d.get('bot'))} – {fmt(d.get('top'))}")
    if d.get("vol") is not None:
        out.append(f"Volume: {fmt(d.get('vol'))}")
    if d.get("pct") is not None:
        out.append(f"Share: {fmt(d.get('pct'))}%")
    return "\n".join(out)


# ---------------------------------------------------------------
# Original format — dir / pattern / symbol / tf / price / low / high / score
# ---------------------------------------------------------------
def msg_legacy(d):
    dir_ = d.get("dir")
    emoji = "🟢" if dir_ == "GREEN" else "🔴" if dir_ == "RED" else "⚪"
    return (
        f"{emoji} <b>{fmt(dir_, '')} {fmt(d.get('pattern'), '')}</b>\n"
        f"Symbol: {fmt(d.get('symbol'), '')}  |  TF: {fmt(d.get('tf'), '')}\n"
        f"Price: {fmt(d.get('price'), '')}\n"
        f"Zone: {fmt(d.get('low'), '')} - {fmt(d.get('high'), '')}\n"
        f"Score: {fmt(d.get('score'), '')}/100"
    )


# ---------------------------------------------------------------
# Candle Detector By Zone Traders W16 2.0 — JSON format
# (only used when the indicator's "Alert format" = JSON;
#  with "Text" the message is passed straight through)
# ---------------------------------------------------------------
def msg_candle(d):
    ev     = str(d.get("event", "")).upper()
    side   = str(d.get("side", "")).upper()
    is_buy = side == "BUY"
    candle = str(d.get("candle", "")).capitalize()

    if ev == "NEW":   # normal mode (Structure Mode OFF)
        icon = "🟢" if candle == "Green" else "🔴" if candle == "Red" else "⚪"
        return "\n".join([
            "🆕 NEW ZONE",
            f"{icon} {fmt(d.get('pattern'))}",
            f"📊 {fmt(d.get('symbol'))} · {fmt(d.get('tf'))}",
            f"🎯 Zone: {fmt(d.get('bottom'))} – {fmt(d.get('top'))}",
            f"⭐ Score: {fmt(d.get('score'))}/100",
        ])

    if ev in ("RETEST", "USED"):
        head = "📍 ZONE TOUCHED"
    elif ev == "HELD":
        head = "📈 ZONE HELD" if is_buy else "📉 ZONE HELD"
    elif ev == "INVALID":
        head = "💥 ZONE BROKEN"
    else:
        head = "🆕 NEW ZONE"

    if ev == "USED":
        icon, ev_tx = "⚪", "USED (box closed)"
    elif ev == "INVALID":
        icon, ev_tx = "❌", "INVALID (box broken)"
    else:
        icon  = "🟢" if is_buy else "🔴"
        ev_tx = "HELD ✅" if ev == "HELD" else ev

    edge = "(box top)" if is_buy else "(box bottom)"
    ct   = "⚠️ Counter Trend (CT)" if d.get("ct") else "✅ Normal"
    return "\n".join([
        head,
        f"{icon} {side} · {ev_tx}",
        f"📊 {fmt(d.get('symbol'))} · {fmt(d.get('tf'))}",
        f"🕯 {fmt(d.get('pattern'))} · {candle} candle",
        f"🎯 Level: {fmt(d.get('level'))} {edge}",
        f"⭐ Score: {fmt(d.get('score'))}/100",
        ct,
    ])


@app.route("/")
def home():
    return "Relay is running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True)
    try:
        d = json.loads(raw)
        src = d.get("src")
        # route on src first, then fall back to the old shape
        if src == "VolOBW16ALT":
            msg = msg_volob_alt(d)
        elif src in ("VolOBW16", "RevZonesW16", "AbsRevW16", "DeltaLadderW16"):
            msg = msg_volob(d)
        elif "dir" in d:
            msg = msg_legacy(d)
        else:
            # unknown JSON — send it readable rather than as one long line
            msg = "<pre>" + json.dumps(d, indent=2) + "</pre>"
    except Exception:
        # not JSON at all (plain-text alert) — pass it straight through
        msg = raw

    send_telegram(msg)
    return "ok", 200


# ---------------------------------------------------------------
# RSI By Zone Traders W16 — separate bot, plain text passed through
# ---------------------------------------------------------------
@app.route("/webhook-rsi", methods=["POST"])
def webhook_rsi():
    raw = request.get_data(as_text=True)
    send_telegram_rsi(raw)
    return "ok", 200


# ---------------------------------------------------------------
# Candle Detector By Zone Traders W16 2.0 — separate bot
# Text format  -> passed straight through
# JSON format  -> formatted by msg_candle (single event or array)
# ---------------------------------------------------------------
@app.route("/webhook-candle", methods=["POST"])
def webhook_candle():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return "empty", 400
    try:
        d = json.loads(raw)
        items = d if isinstance(d, list) else [d]
        for item in items:
            send_telegram_candle(msg_candle(item))
    except Exception:
        # plain-text alert (Alert format = Text) — pass it straight through
        send_telegram_candle(raw)
    return "ok", 200


# ---------------------------------------------------------------
# Vol OB Precision Telegram Alert By Zone Traders W16 — separate bot
# plain text passed straight through
# ---------------------------------------------------------------
@app.route("/webhook-volob-tg", methods=["POST"])
def webhook_volob_tg():
    raw = request.get_data(as_text=True).strip()
    if not raw:
        return "empty", 400
    send_telegram_vobtg(raw)
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
