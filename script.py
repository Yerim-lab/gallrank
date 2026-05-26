import re
import requests
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

BASE = {
    "board": "https://gall.dcinside.com/board/lists/?id={gid}",
    "mgallery": "https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
    "mini": "https://gall.dcinside.com/mini/board/lists/?id={gid}",
}


def resolve_url(url: str):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.url
    except:
        return url


def extract_gid(url: str):
    url = resolve_url(url)
    m = re.search(r"id=([a-zA-Z0-9_]+)", url)
    return m.group(1) if m else None


def is_mini_url(url: str):
    return "/mini/" in url


def is_valid_gallery_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    return bool(
        soup.select_one("tr.ub-content")
        or soup.select_one(".gall_tit")
        or soup.select_one(".gall_listwrap")
    )


def detect_gallery_type(user_url: str):
    url = resolve_url(user_url)
    gid = extract_gid(url)

    if not gid:
        return None, None

    if is_mini_url(url):
        return "mini", url

    for t in ["mgallery", "board"]:
        test_url = BASE[t].format(gid=gid)

        try:
            r = requests.get(test_url, headers=HEADERS, timeout=10)
        except:
            continue

        if r.status_code == 200 and is_valid_gallery_page(r.text):
            return t, test_url

    return None, None


def is_filtered_row(row):
    classes = row.get("class") or []

    if "notice" in classes:
        return True

    num = row.select_one(".gall_num")
    if num and num.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
        return True

    subject = row.select_one(".gall_subject")
    if subject and subject.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
        return True

    return False


def get_writer(row):
    el = row.select_one(".gall_writer") or row.select_one(".ub-writer")

    if not el:
        return "ㅇㅇ"

    return (
        el.get("data-nick")
        or el.get("data-user_nick")
        or el.get("title")
        or el.get_text(strip=True)
        or "ㅇㅇ"
    ).strip() or "ㅇㅇ"


def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if meta:
        return meta.get("content", "").split(" - ")[0].strip()

    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)

    return "갤러리"


def crawl_base(base_url, counter):
    page = 1

    while page <= 100:   # 🔥 핵심 변경: 최근 100페이지 고정
        url = f"{base_url}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("tr.ub-content")

        if not rows:
            break

        for row in rows:
            if is_filtered_row(row):
                continue

            nick = get_writer(row)
            counter[nick] += 1

        page += 1


def crawl_gallery(user_url: str):
    gtype, base_url = detect_gallery_type(user_url)

    if not base_url:
        raise Exception("갤러리 타입 판별 실패")

    counter = Counter()

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        gallery_name = get_gallery_name(soup)
    except:
        gallery_name = extract_gid(user_url)

    crawl_base(base_url, counter)

    total = sum(counter.values())

    result = [
        {
            "rank": i,
            "nickname": nick,
            "count": cnt,
            "share": round(cnt / total * 100, 2) if total else 0
        }
        for i, (nick, cnt) in enumerate(counter.most_common(), 1)
    ]

    return {
        "gallery": gallery_name,
        "type": gtype,
        "total": total,
        "pages": 100,
        "result": result
    }