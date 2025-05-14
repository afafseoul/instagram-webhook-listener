from flask import Flask, request, jsonify, redirect, session, render_template_string
import json
import os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

CLIENT_DB = 'clients.json'
OAUTH_CLIENT_ID = '2883439835182858'
OAUTH_REDIRECT_URI = 'https://instagram-webhook-listener.onrender.com/oauth-callback'
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
OAUTH_SCOPES = 'pages_show_list,instagram_basic,instagram_manage_comments,pages_read_engagement'

def init_db():
    if not os.path.exists(CLIENT_DB):
        with open(CLIENT_DB, 'w') as f:
            json.dump([], f)

def save_client(data):
    with open(CLIENT_DB, 'r') as f:
        clients = json.load(f)

    existing = next((c for c in clients if c['email'] == data['email']), None)
    
    if existing:
        clients = [data if c['email'] == data['email'] else c for c in clients]
    else:
        clients.append(data)

    with open(CLIENT_DB, 'w') as f:
        json.dump(clients, f, indent=2)

@app.route('/')
def home():
    return redirect('/form')

@app.route('/form', methods=['GET'])
def form():
    html = '''
    <h2>Simulation Formulaire de Paiement</h2>
    <form action="/register-new-client" method="post">
        Email: <input type="email" name="email" required><br><br>
        Plan:
        <select name="plan">
            <option value="trial">Essai gratuit (7 jours)</option>
            <option value="basic">Basic (30 jours)</option>
            <option value="pro">Pro (90 jours)</option>
            <option value="premium">Premium (1 an)</option>
        </select><br><br>
        Préférences: <input type="text" name="preferences" placeholder="ex: fun, emojis" required><br><br>
        <input type="submit" value="Payer & Continuer">
    </form>
    '''
    return render_template_string(html)

@app.route('/register-new-client', methods=['POST'])
def register_client():
    email = request.form.get('email')
    plan = request.form.get('plan')
    preferences = request.form.get('preferences')

    if not email or not plan or not preferences:
        return 'Champs manquants', 400

    session['email'] = email
    session['plan'] = plan
    session['preferences'] = preferences

    return redirect('/connect-instagram')

@app.route('/connect-instagram')
def connect_instagram():
    if 'email' not in session:
        return "Accès refusé. Veuillez d'abord payer.", 403

    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={OAUTH_CLIENT_ID}&redirect_uri={OAUTH_REDIRECT_URI}"
        f"&scope={OAUTH_SCOPES}&response_type=code"
    )
    return redirect(oauth_url)

@app.route('/oauth-callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return 'Erreur : aucun code reçu', 400

    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "client_secret": OAUTH_CLIENT_SECRET,
        "code": code
    }
    r = requests.get(token_url, params=params)
    data = r.json()

    if 'access_token' not in data:
        return f"Erreur : {data}", 400

    email = session.get('email')
    plan = session.get('plan')
    preferences = session.get('preferences')
    if not all([email, plan, preferences]):
        return 'Session expirée ou incomplète', 400

    today = datetime.utcnow()
    days = {'trial': 7, 'basic': 30, 'pro': 90, 'premium': 365}.get(plan, 30)

    payload = {
        'email': email,
        'access_token': data['access_token'],
        'plan': plan,
        'preferences': preferences,
        'date_start': today.isoformat(),
        'date_end': (today + timedelta(days=days)).isoformat()
    }
    save_client(payload)

    return 'Connexion réussie ! Votre système est maintenant activé.'

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
