from flask import Flask, request
from webhook import webhook_handler
import threading
from watch_posts import watch_new_posts
from watch_comments import watch_new_comments
from keep_alive import keep_alive

app = Flask(__name__)

# route principale utilisée par Meta Webhook
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    return webhook_handler(request)

def run_watchers():
    threading.Thread(target=watch_new_posts, daemon=True).start()
    threading.Thread(target=watch_new_comments, daemon=True).start()

if __name__ == '__main__':
    print("✅ Lancement Commanda")
    keep_alive()  # démarre le serveur Flask
    run_watchers()
