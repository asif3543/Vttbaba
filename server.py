from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is Alive & Running on Render! Made by OP Developer."

def run_server():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
