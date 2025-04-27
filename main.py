from flask import Flask, request
import requests

app = Flask(__name__)

VERIFY_TOKEN = "your-verify-token"  # <-- À changer avec ton propre token
MAKE_WEBHOOK_URL = "https://hook.make.com/xxxxxxxxxxxxxxx"  # <-- À remplacer par ton lien Make

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        else:
            return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.json
        print("Received webhook:", data)
        requests.post(MAKE_WEBHOOK_URL, json=data)
        return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
