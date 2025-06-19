"""Flask application that continuously checks for new Instagram posts."""

import os
import threading
import time
from flask import Flask

from google_sheet import get_active_pages
from watch_posts import check_new_posts
from reply import send_to_make_webhook

app = Flask(__name__)


def watch_loop() -> None:
    """Background loop checking for new posts."""
    token = os.environ.get("META_SYSTEM_TOKEN")
    webhook = os.environ.get("WEBHOOK_MAKE_POSTS")

    if not token or not webhook:
        print("❌ META_SYSTEM_TOKEN or WEBHOOK_MAKE_POSTS is missing")
        return

    while True:
        try:
            pages = get_active_pages()
        except Exception as exc:
            print(f"❌ Failed to read Google Sheet: {exc}")
            time.sleep(10)
            continue

        for page_id in pages:
            try:
                post = check_new_posts(page_id, token)
                if post:
                    send_to_make_webhook(post, webhook)
            except Exception as exc:
                print(f"❌ Error processing page {page_id}: {exc}")

        time.sleep(10)


@app.route("/")
def index() -> str:
    return "✅ Post watcher running"


def _start_thread() -> None:
    thread = threading.Thread(target=watch_loop, daemon=True)
    thread.start()


_start_thread()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
