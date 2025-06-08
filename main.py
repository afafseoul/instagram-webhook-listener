from flask import Flask, request
from google_sheet import get_active_pages

app = Flask(__name__)
page_ids = []

@app.before_first_request
def initialize():
    print("✅ Lancement Commanda")
    print("🧠 Initialisation du système de commentaires")
    global page_ids
    try:
        page_ids = get_active_pages()
        print("✅ Pages récupérées :", page_ids)
        print("🔁 Boucle de vérification des pages actives :")
        for pid in page_ids:
            print(f"➡️ Page active : {pid['page_id']} (Instagram : {pid['instagram_id']}, Client : {pid['client_name']})")
    except Exception as e:
        print("❌ Erreur lors de la récupération des pages :", e)

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
