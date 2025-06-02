import requests, time, os
from google_sheet import fetch_page_ids

WEBHOOK_COMMENT = os.getenv("MAKE_WEBHOOK_COMMENT")
ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")

last_seen_comments = {}

def get_ig_comments(instagram_id):
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media?fields=id,comments{{id,text,timestamp,username}}&access_token={ACCESS_TOKEN}"
    response = requests.get(url)
    return response.json().get("data", [])

def watch_new_comments():
    print("🟢 Thread watch_comments lancé")
    while True:
        try:
            pages = fetch_page_ids()
            for page in pages:
                ig_id = page['instagram_id']
                if not ig_id:
                    continue

                medias = get_ig_comments(ig_id)
                for media in medias:
                    media_id = media['id']
                    comments = media.get("comments", {}).get("data", [])
                    print(f"🔍 Commentaires pour {media_id}: {comments}")

                    for comment in comments:
                        comment_id = comment['id']
                        if comment_id not in last_seen_comments:
                            last_seen_comments[comment_id] = True
                            requests.post(WEBHOOK_COMMENT, json={
                                "instagram_id": ig_id,
                                "media_id": media_id,
                                "comment": comment
                            })
                            print(f"📩 Nouveau commentaire reçu: {comment_id} (IG ID: {ig_id})")

        except Exception as e:
            print("❌ Erreur dans watch_new_comments:", e)

        time.sleep(30)
