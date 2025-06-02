import time, requests

def keep_alive():
    while True:
        try:
            requests.get("https://commanda.onrender.com/")
            print("🔁 Ping Render OK")
        except Exception as e:
            print("Erreur keep_alive:", e)
        time.sleep(600)
