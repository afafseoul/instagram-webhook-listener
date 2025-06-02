from flask import Flask, request, jsonify
from reply import reply_to_comment

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ API Commanda opérationnelle"

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    data = request.json
    print(f"📥 Donnée reçue via /webhook: {data}")
    return jsonify({"status": "ok"})

@app.route('/reply', methods=['POST'])
def reply_handler():
    data = request.json
    comment_id = data.get("comment_id")
    message = data.get("message")
    if comment_id and message:
        reply_to_comment(comment_id, message)
        return jsonify({"status": "replied"})
    else:
        return jsonify({"error": "Paramètres manquants"}), 400
