from flask import Flask, request, jsonify
import threading
import requests
import os
from google_sheet import get_active_pages
from watch_comments import subscribe_ig_account_to_webhooks, watch_new_comments
from reply import reply_to_comment

app = Flask(__name__)
thread_started = False  # Flag global

def subscribe_all_pages():
    """Abonne tous les comptes Instagram Business configurés aux webhooks."""
    try:
        pages = get_active_pages()
        for page in pages:
            subscribe_ig_account_to_webhooks(page["instagram_id"])
    except Exception as e:
        print(f"❌ Erreur abonnement pages : {e}")

# Souscription immédiate au démarrage de l'application
subscribe_all_pages()

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
        print(
            f"➡️ Page active : {pid['page_id']} (Instagram : {pid['instagram_id']}, Client : {pid['client_name']})"
        )
        subscribe_ig_account_to_webhooks(pid["instagram_id"])

@app.before_request
def start_thread_once():
    global thread_started
    if not thread_started:
        print("🚀 Lancement du thread de surveillance des commentaires")
        threading.Thread(target=watch_new_comments, daemon=True).start()
        thread_started = True

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

                        make_url = os.environ.get("MAKE_WEBHOOK_COMMENT")
                        if make_url:
                            res = requests.post(make_url, json=comment_data)
                            print(f"📤 Envoyé à Make ({res.status_code})")
                        else:
                            print("⚠️ MAKE_WEBHOOK_COMMENT non défini")

        except Exception as e:
            print("❌ Erreur lors du traitement du POST :", e)

        return "ok", 200


@app.route("/reply", methods=["POST"])
def reply_endpoint():
    """Reply to an Instagram comment using the Meta Graph API."""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    comment_id = data.get("comment_id")
    message = data.get("message")

    if not comment_id or not message:
        return jsonify({"error": "comment_id and message are required"}), 400

    try:
        result = reply_to_comment(comment_id, message)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run()
