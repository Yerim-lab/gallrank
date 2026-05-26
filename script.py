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
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://gall.dcinside.com/",
    "Accept-Language": "ko-KR,ko;q=0.9"
}

session = requests.Session()
session.headers.update(HEADERS)


# -----------------------
# 시간 범위
# -----------------------
def get_time_range(days=7):
    now = datetime.now()
    return now - timedelta(days=days), now


# -----------------------
# 갤 이름 추출
# -----------------------
def get_gallery_name(html):
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.select_one("meta[name='description']")
    if not meta:
        return None

    content = meta.get("content", "")
    return content.split(" - ")[0].strip() if " - " in content else content.strip()


# -----------------------
# 날짜 파싱 (title 우선)
# -----------------------
def parse_date(el):
    if not el:
        return None

    try:
        title = el.get("title")
        if title:
            return datetime.strptime(title, "%Y-%m-%d %H:%M:%S")

        text = el.text.strip()
        if re.match(r"^\d{1,2}:\d{2}$", text):
            h, m = map(int, text.split(":"))
            now = datetime.now()
            return now.replace(hour=h, minute=m, second=0, microsecond=0)

    except:
        return None

    return None


# -----------------------
# 제외 필터
# -----------------------
def is_excluded(row):
    subject = row.select_one(".gall_subject")
    if not subject:
        return False

    text = subject.get_text(strip=True)
    return text in ["공지", "AD", "설문"]


# -----------------------
# URL 정규화
# -----------------------
def normalize_url(url):
    parsed = urlparse(url)
    path = parsed.path
    qs = parse_qs(parsed.query)

    gid = qs.get("id", [None])[0]

    if not gid:
        m = re.search(r"id=([^&/]+)", url)
        if m:
            gid = m.group(1)

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
# 차단/이상 HTML 감지
# -----------------------
def is_blocked(html):
    if not html:
        return True

    keywords = [
        "접근", "차단", "보안", "automated", "restricted"
    ]

    return not ("ub-content" in html) or any(k in html.lower() for k in keywords)


# -----------------------
# 크롤러
# -----------------------
def crawl(url):
    list_url = normalize_url(url)

    start, end = get_time_range(7)

    page = 1
    MAX_PAGE = 200

    user_count = defaultdict(int)
    gallery_name = None

    while page <= MAX_PAGE:

        try:
            res = session.get(f"{list_url}&page={page}", timeout=5)
        except Exception as e:
            print("REQUEST ERROR:", e)
            break

        if res.status_code != 200:
            print("STATUS NOT OK:", res.status_code)
            break

        html = res.text

        # 차단 체크
        if page == 1:
            if is_blocked(html):
                print("BLOCK OR INVALID HTML DETECTED")
                break
            gallery_name = get_gallery_name(html)

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr")

        if not rows:
            break

        found = False

        for row in rows:

            if is_excluded(row):
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
                user_count[nick] += 1

        if not found:
            break

        page += 1

    total = sum(user_count.values())

    result = [
        {
            "rank": i,
            "nickname": k,
            "count": v,
            "share": round(v / total * 100, 2) if total else 0
        }
        for i, (k, v) in enumerate(
            sorted(user_count.items(), key=lambda x: x[1], reverse=True),
            1
        )
    ]

    return {
        "gallery": gallery_name,
        "data": result
    }


# -----------------------
# Flask
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/crawl", methods=["POST"])
def api():
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