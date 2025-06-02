from flask import Blueprint, request

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        print(f"🌐 GET reçu : mode={mode}, token={token}, challenge={challenge}")
        if token == "test_token_meta":
            return challenge, 200
        return "❌ Token incorrect", 403

    if request.method == 'POST':
        data = request.get_json()
        print("📩 POST reçu ! Données brutes :")
        print(data)

        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    print(f"🔄 Champ modifié : {change.get('field')}")
                    if change.get("field") == "instagram_comments":
                        print("✅ Nouveau commentaire détecté")
        except Exception as e:
            print(f"❌ Erreur traitement : {e}")

        return "ok", 200
