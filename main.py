# main.py
from flask import Flask, request
import threading
from google_sheet import get_active_pages  # utilise la version hardcodée
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
        entry = request.json.get("entry", [])
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

        return "ok", 200

def watch_comments():
    print("🧠 Début du thread de détection de commentaires")
    try:
        page_ids = get_active_pages()
        print("✅ Pages récupérées :", page_ids)
    except Exception as e:
        print("❌ Erreur lors de la récupération des pages :", e)
        return

    print("🔁 Boucle de vérification des pages actives :")
    for pid in page_ids:
        print(f"➡️ Page active : {pid['page_id']} (Instagram : {pid['instagram_id']}, Client : {pid['client_name']})")

# ✅ Toujours exécuté même si importé
print("✅ Lancement Commanda")
threading.Thread(target=watch_comments).start()
app.run(debug=False, port=10000, host="0.0.0.0")
