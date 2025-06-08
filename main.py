from flask import Flask, request, jsonify
import threading
from google_sheet import get_active_pages
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Webhook listener is up."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        print("🔔 Webhook verification GET reçu")
        return request.args.get("hub.challenge")

    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            print("📥 Données POST reçues :", data)

            entry = data.get("entry", [])
            print(f"📦 Nombre d'éléments dans 'entry': {len(entry)}")

            for change_block in entry:
                changes = change_block.get("changes", [])
                print(f"🔄 Nombre de changements : {len(changes)}")

                for change in changes:
                    field = change.get("field")
                    print(f"🔍 Champ détecté : {field}")
                    if field == "comments":
                        comment_data = change.get("value", {})
                        print("💬 Nouveau commentaire détecté :", comment_data)

        except Exception as e:
            print("❌ Erreur lors du traitement du POST :", e)

        return "ok", 200
