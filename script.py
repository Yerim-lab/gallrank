from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ----------------------------
# 갤러리 이름 추출
# ----------------------------
def get_gallery_title(soup):
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        return og["content"].replace(" - 커뮤니티 포털 디시인사이드", "").strip()

    title = soup.title
    if title:
        return title.text.strip()

    return "알 수 없는 갤러리"


# ----------------------------
# URL 정규화
# ----------------------------
def normalize_url(url):
    url = url.strip()

    if "m.dcinside.com" in url:
        url = url.replace("m.dcinside.com", "gall.dcinside.com")

    if "http" not in url:
        url = f"https://gall.dcinside.com/board/lists/?id={url}"

    return url


# ----------------------------
# 크롤링
# ----------------------------
def crawl(url):
    r = requests.get(url, headers=HEADERS, timeout=10)

    # HTML 아닌 경우 차단 or 오류
    if "text/html" not in r.headers.get("Content-Type", ""):
        raise Exception("HTML 응답이 아님 (차단 가능)")

    soup = BeautifulSoup(r.text, "html.parser")

    gallery = get_gallery_title(soup)

    rows = []

    for tr in soup.select(".us-post tbody tr"):
        try:
            rank = len(rows) + 1

            nickname = tr.select_one(".gall_writer")
            count = tr.select_one(".gall_count")
            share = tr.select_one(".gall_percent")

            if not nickname:
                continue

            rows.append({
                "rank": rank,
                "nickname": nickname.text.strip(),
                "count": int(count.text.strip()) if count else 0,
                "share": share.text.strip() if share else "0"
            })
        except:
            continue

    return {
        "gallery": gallery,
        "result": rows
    }


# ----------------------------
# API
# ----------------------------
@app.route("/api/rank")
def api_rank():
    url = request.args.get("url", "")

    try:
        url = normalize_url(url)
        data = crawl(url)
        return jsonify(data)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# ----------------------------
# Render health check (중요)
# ----------------------------
@app.route("/")
def home():
    return "gallrank running"


# ----------------------------
# 실행 (Render용)
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)