import re
import requests
from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://gall.dcinside.com/"
}


# -----------------------
# URL 정규화
# -----------------------
def normalize_url(url):
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
# 갤 이름 추출
# -----------------------
def get_gallery_name(html):
    soup = BeautifulSoup(html, "html.parser")

    meta = soup.select_one("meta[name='description']")
    if not meta:
        return None

    content = meta.get("content", "")
    return content.split(" - ")[0].strip()


# -----------------------
# 디버그 체크
# -----------------------
def debug_html(html):
    return {
        "has_ub_content": "ub-content" in html,
        "has_gall_date": "gall_date" in html,
        "has_nickname": "nickname" in html,
        "length": len(html)
    }


# -----------------------
# API
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/test", methods=["POST"])
def test():
    url = request.json.get("url")

    try:
        target = normalize_url(url)
        res = requests.get(target, headers=HEADERS, timeout=7)

        html = res.text

        gallery = get_gallery_name(html)
        debug = debug_html(html)

        return jsonify({
            "status": res.status_code,
            "url": target,
            "gallery": gallery,
            "debug": debug,
            "sample": html[:300]
        })

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)