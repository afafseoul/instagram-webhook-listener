import os
import time
import threading
from typing import List, Dict
import requests

from google_sheet import get_instagram_ids
from reply import send_to_make_webhook

ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_MAKE_POST")

seen_posts = set()


def fetch_posts(instagram_id: str) -> List[Dict]:
    """Retrieve posts for a given Instagram Business ID."""
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("data", [])


def check_new_posts() -> None:
    """Check the accounts for new posts and send them to Make if unseen."""
    if not ACCESS_TOKEN:
        raise RuntimeError("META_SYSTEM_TOKEN environment variable is not set")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_MAKE_POST environment variable is not set")

    instagram_ids = get_instagram_ids()
    for ig_id in instagram_ids:
        try:
            posts = fetch_posts(ig_id)
            for post in posts:
                post_id = post.get("id")
                if post_id and post_id not in seen_posts:
                    send_to_make_webhook(post, WEBHOOK_URL)
                    seen_posts.add(post_id)
        except Exception as exc:
            print(f"❌ Error fetching posts for {ig_id}: {exc}")


def watch_new_posts(interval: int = 10) -> None:
    """Continuously watch for new posts every `interval` seconds."""
    print("🟢 Starting post watcher")
    while True:
        check_new_posts()
        time.sleep(interval)


def start_post_watcher(interval: int = 10) -> None:
    """Start the post watcher in a separate daemon thread."""
    thread = threading.Thread(target=watch_new_posts, args=(interval,), daemon=True)
    thread.start()


if __name__ == "__main__":
    watch_new_posts()
