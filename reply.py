import requests, os

ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")

def reply_to_comment(comment_id, message):
    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
    payload = {"message": message, "access_token": ACCESS_TOKEN}
    response = requests.post(url, data=payload)

    if response.ok:
        print(f"✅ Réponse envoyée à {comment_id}")
    else:
        print(f"❌ Erreur en répondant à {comment_id}: {response.text}")
