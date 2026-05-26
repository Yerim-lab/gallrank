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

# -----------------------
# 시간 범위
# -----------------------
def get_time_range(days=7):
    now = datetime.now()
    start = now - timedelta(days=days)
    return start, now


# -----------------------
# DC 시간 파싱
# -----------------------
def parse_dc_date(text: str):
    if not text:
        return None

    text = text.strip()
    now = datetime.now()

    try:
        if re.match(r"^\d{1,2}:\d{2}$", text):
            h, m = map(int, text.split(":"))
            return now.replace(hour=h, minute=m, second=0, microsecond=0)

        if re.match(r"^\d{4}\.\d{1,2}\.\d{1,2}$", text):
            return datetime.strptime(text, "%Y.%m.%d")

        if re.match(r"^\d{1,2}\.\d{1,2}$", text):
            m, d = map(int, text.split("."))
            return datetime(now.year, m, d)

    except:
        return None

    return None


# -----------------------
# URL 정규화
# -----------------------
def normalize_url(url: str):
    parsed = urlparse(url)
    path = parsed.path
    qs = parse_qs(parsed.query)

    gid = qs.get("id", [None])[0]

    if not gid:
        match = re.search(r"id=([^&/]+)", url)
        if match:
            gid = match.group(1)

    if not gid:
        raise ValueError("Invalid URL")

    if "/mgallery" in path:
        base = "https://gall.dcinside.com/mgallery/board/lists?id="
    elif "/mini" in path:
        base = "https://gall.dcinside.com/mini/board/lists?id="
    else:
        base = "https://gall.dcinside.com/board/lists/?id="

    return base + gid


# -----------------------
# 크롤러
# -----------------------
def crawl(url):
    list_url = normalize_url(url)

    start, end = get_time_range(7)

    page = 1
    MAX_PAGE = 200

    user_count = defaultdict(int)

    while page <= MAX_PAGE:
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

        found = False

        for row in rows:
            # 공지/광고/설문 제외
            num_el = row.select_one(".gall_num")
            if num_el:
                t = num_el.text.strip()
                if t in ["공지", "AD", "설문"]:
                    continue

            date_el = row.select_one(".gall_date")
            nick_el = row.select_one(".nickname")

            if not date_el or not nick_el:
                continue

            dt = parse_dc_date(date_el.text)
            if not dt:
                continue

            if start <= dt <= end:
                found = True
                nick = nick_el.text.strip()
                user_count[nick] += 1

        # 완전 종료 조건 (과도한 페이지 탐색 방지)
        if not found:
            break

        page += 1

    total = sum(user_count.values())

    result = []
    for i, (nick, cnt) in enumerate(
        sorted(user_count.items(), key=lambda x: x[1], reverse=True),
        1
    ):
        result.append({
            "rank": i,
            "nickname": nick,
            "count": cnt,
            "share": round(cnt / total * 100, 2) if total else 0
        })

    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    url = request.json.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    try:
        return jsonify(crawl(url))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)