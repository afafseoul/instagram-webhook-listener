from flask import Flask, request
import threading
from post_watcher import watch_new_posts
from comment_watcher import watch_new_comments
from keep_alive import keep_alive
from reply_handler import reply

app = Flask(__name__)

@app.route('/')
def index():
    return '✅ API opérationnelle'

@app.route('/webhook', methods=['POST'])
def webhook():
    from flask import request
    import requests, os
    data = request.json
    print(f"📩 Commentaire reçu : {data}")
    url = os.getenv("MAKE_WEBHOOK_URL_COMMENTS")  # celui des commentaires
    if url:
        requests.post(url, json=data)
    return 'OK', 200

@app.route('/reply', methods=['POST'])
def reply_route():
    return reply()

# Lancer tous les watchers
if __name__ == '__main__':
    threading.Thread(target=watch_new_posts).start()
    threading.Thread(target=watch_new_comments).start()
    threading.Thread(target=keep_alive).start()
    app.run(debug=True)
