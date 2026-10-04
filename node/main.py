import logging
from flask import Flask, jsonify

import node.db

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
logger = logging.getLogger()

@app.route("/")
def index():
    return jsonify({
        "subsearch": "0.1.0"
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)