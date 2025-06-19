"""Functions to detect new Instagram posts for Facebook pages."""

import requests
from typing import Optional, Dict

last_seen: Dict[str, str] = {}


def _get_instagram_id(page_id: str, token: str) -> Optional[str]:
    """Return the Instagram business account ID for the given Facebook page."""
    url = f"https://graph.facebook.com/v19.0/{page_id}"
    params = {"fields": "instagram_business_account", "access_token": token}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        iba = data.get("instagram_business_account", {})
        return iba.get("id")
    except Exception as exc:
        print(f"❌ Failed to get Instagram ID for {page_id}: {exc}")
        return None


def _fetch_latest_post(ig_id: str, token: str) -> Optional[Dict]:
    """Retrieve the latest media post for an Instagram business account."""
    url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
    params = {
        "fields": "id,timestamp,caption,media_type,permalink",
        "limit": 1,
        "access_token": token,
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json().get("data", [])
        return data[0] if data else None
    except Exception as exc:
        print(f"❌ Failed to fetch posts for {ig_id}: {exc}")
        return None


def check_new_posts(page_id: str, token: str) -> Optional[Dict]:
    """Return information about the latest post if it hasn't been seen yet."""
    ig_id = _get_instagram_id(page_id, token)
    if not ig_id:
        return None

    post = _fetch_latest_post(ig_id, token)
    if not post:
        return None

    last_id = last_seen.get(page_id)
    post_id = post.get("id")
    if post_id and post_id != last_id:
        last_seen[page_id] = post_id
        return {
            "page_id": page_id,
            "media_id": post_id,
            "timestamp": post.get("timestamp"),
            "caption": post.get("caption"),
            "media_type": post.get("media_type"),
            "permalink": post.get("permalink"),
        }
    return None
