import requests, time, os
from google_sheet import fetch_page_ids

WEBHOOK_POST = os.getenv("MAKE_WEBHOOK_POST")
ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")

last_seen_posts = {}

def get_ig_posts(instagram_id):
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media?fields=id,caption,timestamp&access_token={ACCESS_TOKEN}"
    response = requests.get(url)
    return response.json().get("data", [])

def watch_new_posts():
    while True:
        try:
            pages = fetch_page_ids()
            for page in pages:
                ig_id = page['instagram_id']
                if not ig_id:
                    continue

                posts = get_ig_posts(ig_id)
                if not posts:
                    continue

                latest_post = posts[0]
                post_id = latest_post['id']
                if ig_id not in last_seen_posts or last_seen_posts[ig_id] != post_id:
                    last_seen_posts[ig_id] = post_id
                    requests.post(WEBHOOK_POST, json={"instagram_id": ig_id, "post_id": post_id})
                    print(f"📤 Nouveau post détecté: {post_id} (IG ID: {ig_id})")

        except Exception as e:
            print("Erreur dans watch_new_posts:", e)

        time.sleep(30)
