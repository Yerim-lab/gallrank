import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36"
}

SKIP = {"공지", "설문", "AD", "광고"}

TIMEOUT = 10


# ----------------------------
# URL 정규화
# ----------------------------
def normalize(url: str):
    url = url.strip()

    # 모바일 → PC
    url = url.replace("https://m.dcinside.com", "https://gall.dcinside.com")

    return url


# ----------------------------
# 갤러리 ID 추출 (mini / mgallery / board / root 대응)
# ----------------------------
def extract_gall_id(url: str):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "id" in qs:
        return qs["id"][0]

    # /board/nouvellevague 같은 구조
    parts = parsed.path.split("/")
    for p in parts[::-1]:
        if p and p not in {"board", "mgallery", "mini", "lists"}:
            return p

    return None


# ----------------------------
# HTML 가져오기 (차단 페이지 대응)
# ----------------------------
def fetch(url: str):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    return r.text


# ----------------------------
# 갤러리 이름 안정 추출
# ----------------------------
def get_gallery_name(soup: BeautifulSoup):
    meta = soup.select_one('meta[name="title"]')
    if meta and meta.get("content"):
        return re.sub(r"\s*-\s*커뮤니티.*$", "", meta["content"]).strip()

    og = soup.select_one('meta[property="og:title"]')
    if og:
        return og["content"].strip()

    title = soup.select_one("title")
    if title:
        return title.text.strip()

    return "Unknown Gallery"


# ----------------------------
# 글 목록 파싱 (누락 방지 핵심)
# ----------------------------
def parse_rows(soup: BeautifulSoup):
    rows = []

    # 디시 구조는 tr 기반
    for tr in soup.select("tr"):
        num = tr.select_one(".gall_num")
        nick = tr.select_one(".gall_writer, .nickname, .user_name, .gall_writer .nickname")
        cnt = tr.select_one(".gall_count")

        if not num or not nick or not cnt:
            continue

        num_text = num.text.strip()

        if num_text in SKIP:
            continue

        nickname = nick.text.strip()

        if not nickname or "undefined" in nickname:
            continue

        try:
            count = int(cnt.text.strip())
        except:
            continue

        rows.append((nickname, count))

    return rows


# ----------------------------
# 핵심 크롤링
# ----------------------------
def crawl(url: str):
    url = normalize(url)
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    gallery = get_gallery_name(soup)
    rows = parse_rows(soup)

    result = {}

    for nick, cnt in rows:
        result[nick] = result.get(nick, 0) + cnt

    sorted_data = sorted(result.items(), key=lambda x: x[1], reverse=True)

    return gallery, sorted_data


# ----------------------------
# API
# ----------------------------
@app.route("/crawl")
def api():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "missing url"}), 400

    try:
        gallery, data = crawl(url)

        total = sum(x[1] for x in data) or 1

        return jsonify({
            "gallery": gallery,
            "data": [
                {
                    "rank": i + 1,
                    "nick": n,
                    "count": c,
                    "share": round(c / total * 100, 2)
                }
                for i, (n, c) in enumerate(data[:200])
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# Render/Gunicorn 대응
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)