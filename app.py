import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

import requests
from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup

app = Flask(__name__)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://gall.dcinside.com/"
})


# -----------------------
# 시간 범위
# -----------------------
def time_range(days=7):
    now = datetime.now()
    return now - timedelta(days=days), now


# -----------------------
# URL 정리
# -----------------------
def normalize(url):
    parsed = urlparse(url)
    path = parsed.path

    gid = parse_qs(parsed.query).get("id", [None])[0]
    if not gid:
        m = re.search(r"id=([^&/]+)", url)
        if m:
            gid = m.group(1)

    if not gid:
        raise ValueError("invalid url")

    if "/mgallery" in path:
        return f"https://gall.dcinside.com/mgallery/board/lists?id={gid}"
    elif "/mini" in path:
        return f"https://gall.dcinside.com/mini/board/lists?id={gid}"
    else:
        return f"https://gall.dcinside.com/board/lists/?id={gid}"


# -----------------------
# 갤 이름
# -----------------------
def gallery_name(html):
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.select_one("meta[name='description']")
    if not meta:
        return None

    return meta.get("content", "").split(" - ")[0].strip()


# -----------------------
# 날짜 파싱
# -----------------------
def parse_date(el):
    try:
        t = el.get("title")
        if t:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

        txt = el.text.strip()
        if re.match(r"^\d{1,2}:\d{2}$", txt):
            h, m = map(int, txt.split(":"))
            now = datetime.now()
            return now.replace(hour=h, minute=m, second=0, microsecond=0)
    except:
        return None


# -----------------------
# 제외
# -----------------------
def skip(row):
    el = row.select_one(".gall_subject")
    if not el:
        return False
    return el.get_text(strip=True) in ["공지", "AD", "설문"]


# -----------------------
# 크롤러
# -----------------------
def crawl(url):
    base = normalize(url)

    start, end = time_range(7)

    page = 1
    max_page = 100

    users = defaultdict(int)
    gname = None

    while page <= max_page:

        try:
            res = session.get(f"{base}&page={page}", timeout=7)
        except Exception as e:
            return {"error": f"request_fail: {str(e)}"}

        if res.status_code != 200:
            return {"error": f"status_{res.status_code}"}

        html = res.text

        if page == 1:
            gname = gallery_name(html)

            # 차단 체크
            if "ub-content" not in html:
                return {
                    "error": "blocked_or_invalid",
                    "sample": html[:300]
                }

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr")

        found = False

        for row in rows:

            if skip(row):
                continue

            date_el = row.select_one(".gall_date")
            nick_el = row.select_one(".nickname")

            if not date_el or not nick_el:
                continue

            dt = parse_date(date_el)
            if not dt:
                continue

            if start <= dt <= end:
                found = True
                nick = nick_el.get_text(strip=True)
                users[nick] += 1

        if not found:
            break

        page += 1

    total = sum(users.values())

    data = [
        {
            "rank": i,
            "nickname": k,
            "count": v,
            "share": round(v / total * 100, 2) if total else 0
        }
        for i, (k, v) in enumerate(
            sorted(users.items(), key=lambda x: x[1], reverse=True),
            1
        )
    ]

    return {
        "gallery": gname,
        "data": data
    }


# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    try:
        url = request.json.get("url")
        if not url:
            return jsonify({"error": "no_url"}), 400

        return jsonify(crawl(url))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Render entry
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)