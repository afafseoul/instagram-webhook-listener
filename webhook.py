import os

def webhook_handler(request):
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == os.getenv("META_VERIFY_TOKEN"):
            print("🔐 Webhook vérifié avec succès.")
            return challenge, 200

        print("❌ Échec de la vérification du webhook.")
        return "Erreur de vérification", 403

    elif request.method == "POST":
        data = request.json
        print("📥 Données reçues via webhook :", data)
        return "Événement reçu", 200

    return "Méthode non supportée", 400
