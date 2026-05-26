import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


# ---------------------------
# 1. URL 정규화 (핵심 강화)
# ---------------------------
def normalize(url: str):
    if not url.startswith("http"):
        url = "https://" + url

    url = url.replace("m.dcinside.com", "gall.dcinside.com")
    return url


# ---------------------------
# 2. ID 추출 (완전 커버)
# ---------------------------
def extract_id(url: str):
    url = normalize(url)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "id" in qs:
        return qs["id"][0]

    # /board/nouvellevague 형태 대응 (핵심)
    m = re.search(r"/board/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    m = re.search(r"/mgallery/board/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    m = re.search(r"/mini/board/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    # fallback
    m = re.search(r"id=([a-zA-Z0-9_]+)", url)
    if m:
        return m.group(1)

    return None


# ---------------------------
# 3. 타입 판별 (정확)
# ---------------------------
def detect_type(url: str):
    url = normalize(url)

    if "mini" in url:
        return "mini"
    if "mgallery" in url:
        return "mgallery"

    # /board/nouvellevague 기본은 "board" 아님 → mgallery fallback 중요
    # DC 특성상 애매한 건 mgallery로 보는 게 안전
    if "/board/" in url:
        return "mgallery"

    return "board"


# ---------------------------
# 4. PC URL 생성 (무조건 이걸 사용)
# ---------------------------
def build_url(gid, t):
    return f"https://gall.dcinside.com/{t}/board/lists/?id={gid}"


# ---------------------------
# 5. 갤러리 이름
# ---------------------------
def gallery_name(soup):
    m = soup.select_one('meta[name="title"]')
    if not m:
        return "갤러리"
    return m.get("content", "").replace(
        " - 커뮤니티 포털 디시인사이드", ""
    ).strip()


# ---------------------------
# 6. 필터
# ---------------------------
def skip(row):
    if "notice" in (row.get("class") or []):
        return True

    for s in [".gall_subject", ".gall_num"]:
        el = row.select_one(s)
        if el and el.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
            return True

    return False


# ---------------------------
# 7. writer
# ---------------------------
def writer(row):
    w = row.select_one(".gall_writer") or row.select_one(".ub-writer")
    if not w:
        return "ㅇㅇ"

    return (
        w.get("data-nick")
        or w.get_text(strip=True)
        or "ㅇㅇ"
    )


# ---------------------------
# 8. 크롤링
# ---------------------------
def crawl(base, counter):
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
        rows = soup.select("tr.ub-content") or soup.select("tr")

        if not rows:
            break

        valid = 0

        for row in rows:
            if skip(row):
                continue

            counter[writer(row)] += 1
            valid += 1

        if valid == 0:
            break

        page += 1


# ---------------------------
# 9. 메인
# ---------------------------
def crawl_gallery(url: str):
    url = normalize(url)

    gid = extract_id(url)
    if not gid:
        raise Exception("갤러리 ID 실패")

    t = detect_type(url)

    base = build_url(gid, t)

    now = datetime.now()
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    try:
        r = requests.get(base, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        name = gallery_name(soup)
    except:
        name = gid

    crawl(base, counter)

    total = sum(counter.values())

    result = []
    for i, (n, c) in enumerate(counter.most_common(), 1):
        result.append({
            "rank": i,
            "nickname": n,
            "count": c,
            "share": round(c / total * 100, 2) if total else 0
        })

    return {
        "gallery": name,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }