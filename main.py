from flask import Flask, request, redirect
import requests
import os
import psycopg2
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
META_APP_ID = os.environ.get("META_APP_ID")
META_APP_SECRET = os.environ.get("META_APP_SECRET")
FROM_EMAIL = os.environ.get("GMAIL_FROM")
TO_EMAIL = os.environ.get("GMAIL_TO")
EMAIL_PASSWORD = os.environ.get("GMAIL_PASS")

def send_email(subject, body):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Commanda", FROM_EMAIL))
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, EMAIL_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())

def store_in_supabase(page_id, page_name, instagram_id):
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO instagram_tokens (page_id, page_name, instagram_id, created_at)
        VALUES (%s, %s, %s, %s)
    """, (page_id, page_name, instagram_id, datetime.utcnow()))
    conn.commit()
    cur.close()
    conn.close()

@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "<h2 style='color:red'>❌ Erreur : Code OAuth manquant</h2>"

    # Échange code contre token
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": "https://instagram-webhook-listener.onrender.com/callback",
        "client_secret": META_APP_SECRET,
        "code": code,
    }
    token_resp = requests.get(token_url, params=params).json()
    access_token = token_resp.get("access_token")

    if not access_token:
        send_email("❌ Échec post-OAuth", "Impossible de récupérer le token d'accès. Vérifiez le code.")
        return "<h2 style='color:red'>❌ Erreur post-OAuth : Token non reçu</h2>"

    # Obtenir les pages disponibles
    pages_resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={"access_token": access_token}).json()
    pages = pages_resp.get("data", [])

    if not pages:
        send_email("❌ Échec post-OAuth", "Aucune page accessible. Le compte Facebook utilisé n'est probablement pas admin total de la page. Assurez-vous que l'utilisateur connecté est bien administrateur de la page Facebook liée au compte Instagram.")
        return "<h2 style='color:red'>❌ Erreur post-OAuth : Aucune page accessible</h2>"

    page = pages[0]  # On prend la première page uniquement
    page_id = page["id"]
    page_name = page.get("name", "")

    # Obtenir l'ID Instagram lié à cette page
    ig_resp = requests.get(f"https://graph.facebook.com/v19.0/{page_id}?fields=connected_instagram_account", params={"access_token": access_token}).json()
    ig = ig_resp.get("connected_instagram_account", {})
    ig_id = ig.get("id")

    if not ig_id:
        send_email("❌ Échec post-OAuth", f"La page <b>{page_name}</b> n'a pas de compte Instagram connecté. Assurez-vous qu'un compte IG est bien lié dans les paramètres de la page.")
        return f"<h2 style='color:red'>❌ Erreur : Aucun compte Instagram relié à la page <b>{page_name}</b></h2>"

    # Enregistrement dans Supabase
    store_in_supabase(page_id, page_name, ig_id)

    # Mail de succès
    email_body = f"""
    <h2>✅ Nouveau token enregistré avec succès</h2>
    <ul>
      <li><b>Page :</b> {page_name}</li>
      <li><b>Instagram :</b> {ig_id}</li>
      <li><b>Page ID :</b> {page_id}</li>
    </ul>
    """
    send_email("✅ Nouveau token client enregistré : " + page_name, email_body)

    # Page affichée au client
    return f"""
    <h2 style='color:green'>✅ Connexion réussie !</h2>
    <p>📄 <b>Page</b> : {page_name}</p>
    <p>📸 <b>Instagram</b> : {ig_id}</p>
    <p style='color:blue'>🟢 Le token a été stocké et un email a été envoyé.</p>
    <a href='/'>Retour</a>
    """

if __name__ == "__main__":
    app.run(debug=True)
