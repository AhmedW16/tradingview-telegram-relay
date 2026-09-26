import os
import json
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    import requests
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
