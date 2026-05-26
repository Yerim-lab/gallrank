import os
import re
from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ----------------------------
# 1. URL NORMALIZER (핵심)
# ----------------------------
def normalize_dc_url(url: str):
    """
    return:
    - type: board | mgallery | mini
    - id: gallery id
    - list_url: 크롤링용 URL
    """

    url = url.strip()

    parsed = urlparse(url)
    path = parsed.path
    qs = parse_qs(parsed.query)

    # id 추출
    gallery_id = None

    if "id" in qs:
        gallery_id = qs["id"][0]

    # /mini/wendy 형태
    match = re.search(r"/mini/([^/?]+)", path)
    if match:
        gallery_type = "mini"
        gallery_id = gallery_id or match.group(1)

    # /mgallery/wendy 또는 /mgallery/board/lists
    elif "/mgallery" in path:
        gallery_type = "mgallery"
        if not gallery_id:
            match = re.search(r"/mgallery/(?:board/lists|[^/?]+)", path)
            if match:
                gallery_id = match.group(0).split("/")[-1]

    # /board or root
    else:
        gallery_type = "board"
        if not gallery_id:
            match = re.search(r"/(board|gallery)/?([^/?]+)?", path)
            if match and match.group(2):
                gallery_id = match.group(2)

    if not gallery_id:
        raise ValueError("Invalid DCInside URL")

    # 정규화된 리스트 URL 생성
    if gallery_type == "board":
        list_url = f"https://gall.dcinside.com/board/lists/?id={gallery_id}"
    elif gallery_type == "mgallery":
        list_url = f"https://gall.dcinside.com/mgallery/board/lists?id={gallery_id}"
    else:
        list_url = f"https://gall.dcinside.com/mini/board/lists?id={gallery_id}"

    return gallery_type, gallery_id, list_url


# ----------------------------
# 2. MVP CRAWLER (placeholder)
# ----------------------------
def crawl_gallery(url):
    gtype, gid, list_url = normalize_dc_url(url)

    print("[DEBUG]", gtype, gid, list_url)

    # MVP 더미 (여기서 실제 크롤링 붙이면 됨)
    result = [
        {"rank": 1, "nickname": "test", "id": "user1", "count": 10, "share": 50.0},
        {"rank": 2, "nickname": "test2", "id": "user2", "count": 5, "share": 25.0},
    ]

    return result


# ----------------------------
# 3. ROUTES
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/crawl", methods=["POST"])
def crawl():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    try:
        result = crawl_gallery(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ----------------------------
# RUN (Render)
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)