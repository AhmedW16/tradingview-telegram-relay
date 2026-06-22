from flask import Flask, request
import requests, os, json

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

@app.route("/")
def home():
    return "Relay is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True)
    try:
        d = json.loads(raw)
        emoji = "🟢" if d.get("dir") == "GREEN" else "🔴" if d.get("dir") == "RED" else "⚪"
        msg = (
            f"{emoji} <b>{d.get('dir','')} {d.get('pattern','')}</b>\n"
            f"Symbol: {d.get('symbol','')}  |  TF: {d.get('tf','')}\n"
            f"Price: {d.get('price','')}\n"
            f"Zone: {d.get('low','')} - {d.get('high','')}\n"
            f"Score: {d.get('score','')}/100"
        )
    except Exception:
        msg = raw
    send_telegram(msg)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
