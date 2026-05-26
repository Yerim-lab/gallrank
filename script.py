from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ----------------------------
# URL 정규화 (핵심)
# ----------------------------
def normalize_url(url: str) -> str:
    url = url.strip()

    # 모바일 → PC
    url = url.replace("m.dcinside.com", "gall.dcinside.com")

    # mini / mgallery / gall 자동 유지
    if "http" not in url:
        url = f"https://gall.dcinside.com/board/lists/?id={url}"

    return url


# ----------------------------
# 차단 페이지 감지
# ----------------------------
def is_blocked(html: str) -> bool:
    keywords = [
        "We are with you all the way",
        "IT is Life",
        "차단",
        "접근이 제한"
    ]
    return any(k in html for k in keywords)


# ----------------------------
# 갤러리 이름 추출 (정확 버전)
# ----------------------------
def get_gallery_name(soup: BeautifulSoup) -> str:
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        title = og["content"]
        return title.replace(" - 커뮤니티 포털 디시인사이드", "").strip()

    h1 = soup.select_one("h2, h1")
    if h1:
        return h1.text.strip()

    return "알 수 없는 갤러리"


# ----------------------------
# 리스트 파싱
# ----------------------------
def parse_rows(soup: BeautifulSoup):
    rows = []

    # DCinside 구조 변화 대응 (여러 selector 시도)
    selectors = [
        ".us-post tbody tr",
        ".gall_list tbody tr",
        "tr.ub-content"
    ]

    for sel in selectors:
        trs = soup.select(sel)
        if trs:
            for tr in trs:
                try:
                    nickname_el = tr.select_one(".gall_writer, .ub-writer")
                    count_el = tr.select_one(".gall_count")
                    share_el = tr.select_one(".gall_percent")

                    if not nickname_el:
                        continue

                    nickname = nickname_el.text.strip()

                    # 광고/공지 제거
                    if nickname in ["관리자", "운영자", "설문"]:
                        continue

                    count = int(count_el.text.strip()) if count_el and count_el.text.strip().isdigit() else 0
                    share = share_el.text.strip() if share_el else "0"

                    rows.append({
                        "rank": len(rows) + 1,
                        "nickname": nickname,
                        "count": count,
                        "share": share
                    })

                except:
                    continue

            break

    return rows


# ----------------------------
# 크롤러
# ----------------------------
def crawl(url: str):
    url = normalize_url(url)

    r = requests.get(url, headers=HEADERS, timeout=10)
    html = r.text

    if is_blocked(html):
        raise Exception("DCinside 차단 페이지 감지 (IP/UA 제한 가능)")

    soup = BeautifulSoup(html, "html.parser")

    gallery = get_gallery_name(soup)
    result = parse_rows(soup)

    return {
        "gallery": gallery,
        "result": result
    }


# ----------------------------
# API
# ----------------------------
@app.route("/api/rank")
def api_rank():
    url = request.args.get("url", "")

    if not url:
        return jsonify({"error": "url 없음"}), 400

    try:
        data = crawl(url)
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------
# 프론트 (HTML 직접 포함)
# ----------------------------
HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>갤창랭킹</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body { font-family: Arial; padding:20px; }
input { width:70%; padding:10px; }
button { padding:10px; }
table { width:100%; margin-top:20px; border-collapse: collapse; }
td,th { border:1px solid #ddd; padding:8px; text-align:center; }
</style>
</head>

<body>

<h2>갤창랭킹</h2>

<input id="url">
<button onclick="run()">검색</button>

<div id="out"></div>

<script>
async function run(){
    const url = document.getElementById("url").value;

    const res = await fetch("/api/rank?url=" + encodeURIComponent(url));
    const data = await res.json();

    if(data.error){
        document.getElementById("out").innerText = data.error;
        return;
    }

    let html = "<h3>" + data.gallery + "</h3>";
    html += "<table><tr><th>순위</th><th>닉네임</th><th>글수</th><th>지분</th></tr>";

    data.result.forEach(r=>{
        html += `<tr>
            <td>${r.rank}</td>
            <td>${r.nickname}</td>
            <td>${r.count}</td>
            <td>${r.share}%</td>
        </tr>`;
    });

    html += "</table>";

    document.getElementById("out").innerHTML = html;
}
</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


# ----------------------------
# run
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)