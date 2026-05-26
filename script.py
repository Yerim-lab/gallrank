import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}

SKIP_KEYWORDS = {"공지", "설문", "AD", "광고"}

def normalize_url(url: str):
    url = url.strip()

    # 모바일 → 데스크탑 변환
    url = url.replace("https://m.dcinside.com", "https://gall.dcinside.com")

    # mini/mgallery/board 유지
    return url


def extract_gallery_name(soup: BeautifulSoup):
    # 1순위: meta title
    meta = soup.select_one('meta[name="title"]')
    if meta and meta.get("content"):
        title = meta["content"]
        # " - 커뮤니티 포털 디시인사이드" 제거
        title = re.sub(r"\s*-\s*커뮤니티.*$", "", title).strip()
        return title

    # 2순위: og:title
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        return og["content"].strip()

    # 3순위 fallback
    h = soup.select_one("title")
    if h:
        return h.text.strip()

    return "Unknown Gallery"


def extract_gall_id(url: str):
    parsed = urlparse(url)

    # /board/lists/?id=xxx
    q = parse_qs(parsed.query)
    if "id" in q:
        return q["id"][0]

    # /board/xxx
    parts = parsed.path.split("/")
    for p in parts:
        if p and p not in {"board", "lists", "mgallery", "mini"}:
            return p

    return None


def fetch_html(url: str):
    r = requests.get(url, headers=HEADERS, timeout=10)

    # 디시 봇 페이지 차단 대응
    if "IT is Life" in r.text or "<html" in r.text.lower():
        return r.text

    return r.text


def parse_rows(soup: BeautifulSoup):
    rows = []

    candidates = soup.select("tr")

    for tr in candidates:
        num = tr.select_one(".gall_num")
        nick = tr.select_one(".gall_writer, .nickname, .user_name")
        cnt = tr.select_one(".gall_count")
        share = tr.select_one(".gall_recommend, .gall_share")

        if not (num and nick and cnt):
            continue

        num_text = num.text.strip()

        # 필터
        if num_text in SKIP_KEYWORDS:
            continue

        nickname = nick.text.strip()

        # undefined 방지
        if not nickname or "undefined" in nickname:
            continue

        try:
            post_count = int(cnt.text.strip())
        except:
            continue

        try:
            share_val = share.text.strip() if share else "0"
        except:
            share_val = "0"

        rows.append((nickname, post_count, share_val))

    return rows


def crawl(url: str):
    url = normalize_url(url)
    html = fetch_html(url)

    soup = BeautifulSoup(html, "html.parser")

    gallery_name = extract_gallery_name(soup)

    rows = parse_rows(soup)

    # 집계 (닉네임 기준)
    counter = {}

    for nick, cnt, share in rows:
        counter[nick] = counter.get(nick, 0) + cnt

    sorted_data = sorted(counter.items(), key=lambda x: x[1], reverse=True)

    return gallery_name, sorted_data


if __name__ == "__main__":
    url = input().strip()

    name, data = crawl(url)

    print(name)

    for i, (nick, cnt) in enumerate(data[:200], 1):
        share = cnt / max(1, sum(x[1] for x in data)) * 100
        print(f"{i}\t{nick}\t{cnt}\t{share:.2f}%")