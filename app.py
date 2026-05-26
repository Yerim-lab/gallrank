import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

import requests
from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup

app = Flask(__name__)

# -----------------------
# 모바일 세션 고정
# -----------------------
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Referer": "https://m.dcinside.com/",
    "Accept-Language": "ko-KR,ko;q=0.9"
})


# -----------------------
# 시간 범위
# -----------------------
def get_range(days=7):
    now = datetime.now()
    return now - timedelta(days=days), now


# -----------------------
# m.dcinside URL 강제 변환
# -----------------------
def normalize_to_mobile(url):
    parsed = urlparse(url)
    path = parsed.path

    gid = parse_qs(parsed.query).get("id", [None])[0]

    if not gid:
        m = re.search(r"id=([^&/]+)", url)
        if m:
            gid = m.group(1)

    if not gid:
        raise ValueError("invalid url")

    # mini / mgallery / board 모두 m.dcinside로 통일
    if "/mini" in path:
        return f"https://m.dcinside.com/mini/{gid}"
    elif "/mgallery" in path:
        return f"https://m.dcinside.com/mgallery/{gid}"
    else:
        return f"https://m.dcinside.com/board/{gid}"


# -----------------------
# 갤러리 이름
# -----------------------
def gallery_name(html):
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.select_one("meta[name='description']")
    if meta:
        return meta.get("content", "").split(" - ")[0].strip()

    title = soup.select_one("title")
    if title:
        return title.get_text(strip=True)

    return None


# -----------------------
# 날짜 파싱 (m 기준 대응)
# -----------------------
def parse_date(el):
    try:
        txt = el.get_text(strip=True)

        # 2026.05.26 13:22
        m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s+(\d{1,2}):(\d{2})", txt)
        if m:
            y, mo, d, h, mi = map(int, m.groups())
            return datetime(y, mo, d, h, mi)

        # HH:MM (오늘)
        if re.match(r"^\d{1,2}:\d{2}$", txt):
            h, mi = map(int, txt.split(":"))
            now = datetime.now()
            return now.replace(hour=h, minute=mi, second=0, microsecond=0)

        # title fallback
        t = el.get("title")
        if t:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

    except:
        return None

    return None


# -----------------------
# 제외 대상
# -----------------------
def is_skip(row):
    el = row.select_one(".gall_subject")
    if not el:
        return False

    return el.get_text(strip=True) in ["공지", "AD", "설문"]


# -----------------------
# 작성자 fallback (m 대응)
# -----------------------
def get_writer(row):
    return (
        row.select_one(".nickname") or
        row.select_one(".gall_writer") or
        row.select_one(".writer") or
        row.select_one("td")
    )


# -----------------------
# 날짜 fallback
# -----------------------
def get_date(row):
    return (
        row.select_one(".gall_date") or
        row.select_one(".date_time") or
        row.select_one(".time")
    )


# -----------------------
# 크롤러
# -----------------------
def crawl(url):
    base = normalize_to_mobile(url)

    start, end = get_range(7)

    page = 1
    MAX_PAGE = 50

    users = defaultdict(int)
    gname = None

    while page <= MAX_PAGE:

        try:
            res = session.get(f"{base}?page={page}", timeout=7)
        except Exception as e:
            return {"error": f"request_fail: {str(e)}"}

        if res.status_code != 200:
            return {"error": f"status_{res.status_code}"}

        html = res.text

        if page == 1:
            gname = gallery_name(html)

            # m.dcinside 최소 구조 체크
            if "m.dcinside.com" not in res.url and "gallery" not in html:
                return {
                    "error": "blocked_or_invalid_html",
                    "sample": html[:300]
                }

        soup = BeautifulSoup(html, "html.parser")

        # m 페이지 대응 row selector
        rows = (
            soup.select("li.ub-content") or
            soup.select("tr.ub-content") or
            soup.select("div.ub-content") or
            soup.select("li") or
            soup.select("tr")
        )

        found = False

        for row in rows:

            if is_skip(row):
                continue

            date_el = get_date(row)
            writer_el = get_writer(row)

            if not date_el or not writer_el:
                continue

            dt = parse_date(date_el)
            if not dt:
                continue

            if start <= dt <= end:
                found = True
                name = writer_el.get_text(strip=True)
                users[name] += 1

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


# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)