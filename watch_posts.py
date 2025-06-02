def check_posts(page_id):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed?access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        data = response.json()
        print(f"[{page_id}] ✅ Posts reçus :", data)
        requests.post(WEBHOOK_URL, json=data)  # vers `MAKE_WEBHOOK_POST`
    except Exception as e:
        print(f"[{page_id}] ❌ Erreur récupération posts :", e)
