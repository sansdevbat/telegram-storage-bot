from flask import Flask, jsonify
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'alive',
        'message': 'Bot is running!',
        'timestamp': time.time()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
