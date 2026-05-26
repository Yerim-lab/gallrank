import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
}


# -----------------------
# URL normalize
# -----------------------
def normalize(url):
    if not url.startswith("http"):
        url = "https://" + url
    return url


def extract_id(url):
    url = normalize(url)

    m = re.search(r"id=([a-zA-Z0-9_]+)", url)
    if m:
        return m.group(1)

    m = re.search(r"dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", url)
    if m:
        return m.group(1)

    m = re.search(r"dcinside\.com/([a-zA-Z0-9_]+)$", url)
    if m:
        return m.group(1)

    return None


# -----------------------
# 갤러리 타입 자동 판별 (중요)
# -----------------------
def detect_type(url):
    if "/mini/" in url:
        return "mini"
    if "/mgallery/" in url:
        return "mgallery"
    return "board"


def build_url(gid, t):
    if t == "mini":
        return f"https://gall.dcinside.com/mini/board/lists/?id={gid}"
    if t == "mgallery":
        return f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}"
    return f"https://gall.dcinside.com/board/lists/?id={gid}"


# -----------------------
# 필터
# -----------------------
def skip(row):
    if "notice" in (row.get("class") or []):
        return True

    t = row.get_text(" ", strip=True)
    if any(x in t for x in ["공지", "설문", "AD", "광고"]):
        return True

    return False


# -----------------------
# 날짜 (없어도 허용)
# -----------------------
def parse_date(row):
    el = row.select_one(".gall_date")
    if not el:
        return None

    title = el.get("title")
    if title:
        try:
            return datetime.strptime(title, "%Y-%m-%d %H:%M:%S")
        except:
            pass

    return None


# -----------------------
# writer 안정 추출
# -----------------------
def writer(row):
    el = row.select_one(".gall_writer") or row.select_one(".ub-writer")

    if not el:
        return "ㅇㅇ"

    v = el.get("data-nick") or el.get_text(strip=True)
    v = v.strip()

    if not v or v == "undefined":
        return "ㅇㅇ"

    return v


# -----------------------
# crawl
# -----------------------
def crawl(base, cutoff, counter):
    page = 1

    while page <= 200:
        url = f"{base}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")

        rows = soup.select("tr.ub-content")
        if not rows:
            rows = soup.select("tr")

        if not rows:
            break

        for row in rows:
            if skip(row):
                continue

            w = writer(row)

            # 핵심: dt 없어도 포함 (누락 방지)
            dt = parse_date(row)

            if dt and dt < cutoff:
                continue

            counter[w] += 1

        page += 1


# -----------------------
# main
# -----------------------
def crawl_gallery(url):
    url = normalize(url)
    gid = extract_id(url)

    if not gid:
        raise Exception("ID 실패")

    now = datetime.now()

    # 정확히 7일 전 00:00
    cutoff = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    counter = Counter()

    gtype = detect_type(url)
    base = build_url(gid, gtype)

    crawl(base, cutoff, counter)

    total = sum(counter.values())

    result = []
    rank = 1

    for k, v in counter.most_common():
        result.append({
            "rank": rank,
            "nickname": k,
            "count": v,
            "share": round(v / total * 100, 2) if total else 0
        })
        rank += 1

    return {
        "gallery": gid,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }