import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

import requests
from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ---------------------------
# 1. 시간 범위
# ---------------------------
def get_time_range(days=7):
    now = datetime.now()
    start = (now - timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, now


# ---------------------------
# 2. DC 날짜 파싱
# ---------------------------
def parse_dc_date(text):
    text = text.strip()
    now = datetime.now()

    try:
        # HH:MM (오늘)
        if ":" in text:
            h, m = map(int, text.split(":"))
            return now.replace(hour=h, minute=m, second=0, microsecond=0)

        # YYYY.MM.DD
        if text.count(".") == 2:
            return datetime.strptime(text, "%Y.%m.%d")

        # MM.DD
        if text.count(".") == 1:
            m, d = map(int, text.split("."))
            return datetime(now.year, m, d)

    except:
        return None

    return None


# ---------------------------
# 3. URL 정규화
# ---------------------------
def normalize_dc_url(url: str):
    url = url.strip()
    parsed = urlparse(url)
    path = parsed.path
    qs = parse_qs(parsed.query)

    gid = qs.get("id", [None])[0]

    gtype = "board"

    if "/mini" in path:
        gtype = "mini"
        match = re.search(r"/mini/(?:board/lists/)?([^/?]+)", path)
        if match and not gid:
            gid = match.group(1)

    elif "/mgallery" in path:
        gtype = "mgallery"
        match = re.search(r"id=([^&/]+)", url)
        if match and not gid:
            gid = match.group(1)

    else:
        gtype = "board"
        match = re.search(r"id=([^&/]+)", url)
        if match and not gid:
            gid = match.group(1)

    if not gid:
        raise ValueError("Invalid DCInside URL")

    if gtype == "board":
        list_url = f"https://gall.dcinside.com/board/lists/?id={gid}"
    elif gtype == "mgallery":
        list_url = f"https://gall.dcinside.com/mgallery/board/lists?id={gid}"
    else:
        list_url = f"https://gall.dcinside.com/mini/board/lists?id={gid}"

    return gtype, gid, list_url


# ---------------------------
# 4. 끌올 대응 종료 조건
# ---------------------------
def should_stop(pages_without_hit, threshold=2):
    return pages_without_hit >= threshold


# ---------------------------
# 5. 크롤러 핵심
# ---------------------------
def crawl_gallery(url):
    gtype, gid, list_url = normalize_dc_url(url)

    start, end = get_time_range(7)

    page = 1
    user_count = defaultdict(int)

    pages_without_hit = 0
    MAX_EMPTY_PAGES = 2
    MAX_PAGE_LIMIT = 200

    while True:
        if page > MAX_PAGE_LIMIT:
            break

        try:
            res = requests.get(f"{list_url}&page={page}", headers=HEADERS, timeout=5)
        except:
            break

        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("tr.ub-content")

        if not rows:
            break

        page_has_valid = False

        for row in rows:
            date_el = row.select_one(".gall_date")
            nick_el = row.select_one(".nickname")

            if not date_el or not nick_el:
                continue

            post_time = parse_dc_date(date_el.text)

            if not post_time:
                continue

            # 기간 필터
            if start <= post_time <= end:
                page_has_valid = True

                nickname = nick_el.text.strip()
                uid = nickname  # MVP 단계

                user_count[(nickname, uid)] += 1

        # 페이지 단위 끌올 대응
        if page_has_valid:
            pages_without_hit = 0
        else:
            pages_without_hit += 1

        if should_stop(pages_without_hit, MAX_EMPTY_PAGES):
            break

        page += 1

    total = sum(user_count.values())

    result = []
    for i, ((nick, uid), cnt) in enumerate(
        sorted(user_count.items(), key=lambda x: x[1], reverse=True),
        1
    ):
        result.append({
            "rank": i,
            "nickname": nick,
            "id": uid,
            "count": cnt,
            "share": round(cnt / total * 100, 2) if total else 0
        })

    return result


# ---------------------------
# 6. Flask Routes
# ---------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    try:
        result = crawl_gallery(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# 7. Render Run
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)