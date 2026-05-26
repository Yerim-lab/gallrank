from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SKIP_KEYWORDS = {"공지", "설문", "AD", "광고"}


def normalize_url(url):
    return url.replace("https://m.dcinside.com", "https://gall.dcinside.com")


def extract_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if meta and meta.get("content"):
        title = meta["content"]
        return re.sub(r"\s*-\s*커뮤니티.*$", "", title).strip()

    og = soup.select_one('meta[property="og:title"]')
    if og:
        return og["content"].strip()

    t = soup.select_one("title")
    return t.text.strip() if t else "Unknown"


def parse_rows(soup):
    rows = []

    for tr in soup.select("tr"):
        num = tr.select_one(".gall_num")
        nick = tr.select_one(".gall_writer, .nickname, .user_name")
        cnt = tr.select_one(".gall_count")

        if not num or not nick or not cnt:
            continue

        if num.text.strip() in SKIP_KEYWORDS:
            continue

        name = nick.text.strip()
        if not name or "undefined" in name:
            continue

        try:
            c = int(cnt.text.strip())
        except:
            continue

        rows.append((name, c))

    return rows


def crawl(url):
    url = normalize_url(url)

    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    name = extract_gallery_name(soup)
    rows = parse_rows(soup)

    result = {}

    for n, c in rows:
        result[n] = result.get(n, 0) + c

    sorted_data = sorted(result.items(), key=lambda x: x[1], reverse=True)

    return name, sorted_data


@app.route("/crawl")
def api():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "missing url"}), 400

    try:
        name, data = crawl(url)

        total = sum(x[1] for x in data) or 1

        return jsonify({
            "gallery": name,
            "data": [
                {
                    "nick": n,
                    "count": c,
                    "share": round(c / total * 100, 2)
                }
                for n, c in data[:200]
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)