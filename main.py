from flask import Flask, request, redirect, render_template_string, session
import requests
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecret")
CLIENT_DB = "clients.json"

@app.route('/')
def index():
    return '🏠 API Commanda opérationnelle.'

@app.route('/oauth-callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return "Erreur : aucun code reçu", 400

    # Échanger le code contre un access_token Meta
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": "2883439835182858",
        "redirect_uri": "https://instagram-webhook-listener.onrender.com/oauth-callback",
        "client_secret": os.environ.get("FB_CLIENT_SECRET"),
        "code": code
    }
    res = requests.get(token_url, params=params)
    data = res.json()

    access_token = data.get("access_token")
    if not access_token:
        return f"Erreur d'obtention du token : {data}", 400

    # Récupérer la page Facebook associée
    page_name = "Non détectée"
    try:
        page_req = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={
            "access_token": access_token
        })
        page_data = page_req.json()
        page_name = page_data.get("data", [{}])[0].get("name", "Inconnue")
    except:
        pass

    # Exemple d'infos associées — à adapter selon ton système réel
    email = session.get("email", "test@ece-cook.com")
    plan = session.get("plan", "Free")
    preferences = session.get("preferences", "Style par défaut")
    date_start = datetime.now().isoformat()
    date_end = (datetime.now() + timedelta(days=30)).isoformat()

    # Sauvegarde dans le JSON local
    payload = {
        "email": email,
        "plan": plan,
        "preferences": preferences,
        "date_start": date_start,
        "date_end": date_end,
        "page_name": page_name
    }

    try:
        with open(CLIENT_DB, 'r') as f:
            clients = json.load(f)
    except FileNotFoundError:
        clients = []

    clients = [c for c in clients if c['email'] != email]  # éviter les doublons
    clients.append(payload)

    with open(CLIENT_DB, 'w') as f:
        json.dump(clients, f, indent=2)

    return render_template_string(f"""
    <html>
      <head><title>Connexion réussie</title></head>
      <body style="font-family: sans-serif; padding: 2em;">
        <h2>✅ Connexion Meta réussie</h2>
        <p>L’automatisation est maintenant activée pour :</p>
        <ul>
          <li><strong>Email :</strong> {email}</li>
          <li><strong>Plan :</strong> {plan}</li>
          <li><strong>Préférences :</strong> {preferences}</li>
          <li><strong>Page Facebook :</strong> {page_name}</li>
          <li><strong>Du :</strong> {date_start[:10]} au {date_end[:10]}</li>
        </ul>
        <a href="https://cozy-maamoul-92d86f.netlify.app/dashboard.html">↩️ Retour au dashboard</a>
      </body>
    </html>
    """)

@app.route('/linked-pages')
def linked_pages():
    email = session.get("email", "test@ece-cook.com")

    try:
        with open(CLIENT_DB, 'r') as f:
            clients = json.load(f)
    except FileNotFoundError:
        return "Aucune donnée client enregistrée.", 404

    client = next((c for c in clients if c['email'] == email), None)
    if not client:
        return "Client introuvable.", 404

    return render_template_string(f"""
    <html>
      <head><title>Pages liées</title></head>
      <body style="font-family: sans-serif; padding: 2em;">
        <h2>📄 Détail de la page liée</h2>
        <ul>
          <li><strong>Email :</strong> {client['email']}</li>
          <li><strong>Plan :</strong> {client['plan']}</li>
          <li><strong>Préférences :</strong> {client['preferences']}</li>
          <li><strong>Page Facebook :</strong> {client['page_name']}</li>
          <li><strong>Du :</strong> {client['date_start'][:10]} au {client['date_end'][:10]}</li>
        </ul>
      </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(debug=True)
