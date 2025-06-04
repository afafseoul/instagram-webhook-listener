# main.py
from flask import Flask, request
import threading
from utils.google_sheet import get_sheet_page_ids
from utils.config_test import HARDCODED_PAGE_IDS, USE_HARDCODED_IDS
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
        print("📥 Données POST reçues :", request.json)
        changes = request.json.get("entry", [{}])[0].get("changes", [])
        for change in changes:
            if change.get("field") == "comments":
                comment_data = change.get("value", {})
                print("💬 Nouveau commentaire détecté :", comment_data)
        return "ok", 200

def watch_comments():
    print("🧠 Début du thread de détection de commentaires")
    page_ids = []

    if USE_HARDCODED_IDS:
        print("⚙️ Utilisation des IDs en dur dans le code")
        page_ids = HARDCODED_PAGE_IDS
    else:
        print("🔍 Tentative d'accès au Google Sheet...")
        try:
            page_ids = get_sheet_page_ids()
            print("✅ Google Sheet accessible. IDs détectés :", page_ids)
        except Exception as e:
            print("❌ Erreur lors de la lecture du Google Sheet :", e)

    # Simuler un listener webhook pour chaque ID (ou juste montrer qu'on les a)
    print("🔁 Boucle de vérification des pages actives :")
    for pid in page_ids:
        print("➡️ Page active :", pid)

if __name__ == "__main__":
    print("✅ Lancement Commanda")
    threading.Thread(target=watch_comments).start()
    app.run(debug=False, port=10000, host="0.0.0.0")
