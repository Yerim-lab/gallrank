import os
from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -------------------
# Front page (Jinja)
# -------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------------
# API
# -------------------
@app.route("/api/crawl", methods=["POST"])
def crawl():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    # MVP 더미 (크롤링 자리)
    result = [
        {"rank": 1, "nickname": "userA", "id": "aaa", "count": 12, "share": 60.0},
        {"rank": 2, "nickname": "userB", "id": "bbb", "count": 8, "share": 40.0},
    ]

    return jsonify(result)


# -------------------
# Favicon
# -------------------
@app.route("/favicon.png")
def favicon():
    return app.send_static_file("../favicon.png")


# -------------------
# Run (Render 필수)
# -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)