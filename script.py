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
# URL 정규화
# ---------------------------
def normalize_url(url: str):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


# ---------------------------
# gallery id 추출 (모든 케이스)
# ---------------------------
def extract_gallery_id(url: str):
    url = normalize_url(url)

    qs = parse_qs(urlparse(url).query)
    if "id" in qs:
        return qs["id"][0]

    patterns = [
        r"dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)",
        r"m\.dcinside\.com/board/([a-zA-Z0-9_]+)",
        r"dcinside\.com/([a-zA-Z0-9_]+)$"
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# ---------------------------
# 날짜 파싱
# ---------------------------
def parse_post_date(row):
    el = row.select_one(".gall_date")
    if not el:
        return None

    title = el.get("title")
    if title:
        try:
            return datetime.strptime(title, "%Y-%m-%d %H:%M:%S")
        except:
            pass

    text = el.get_text(strip=True)
    now = datetime.now()

    if re.match(r"^\d{1,2}:\d{2}$", text):
        h, m = map(int, text.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    return None


# ---------------------------
# writer 파싱 안정화
# ---------------------------
def parse_writer(row):
    w = row.select_one(".gall_writer") or row.select_one(".ub-writer")
    if not w:
        return "ㅇㅇ"

    nick = w.get("data-nick") or w.get_text(strip=True)
    if not nick:
        return "ㅇㅇ"

    return nick.strip()


# ---------------------------
# 필터
# ---------------------------
def is_filtered(row):
    if "notice" in (row.get("class") or []):
        return True

    num = row.select_one(".gall_num")
    if num and num.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
        return True

    subject = row.select_one(".gall_subject")
    if subject and subject.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
        return True

    return False


# ---------------------------
# base url 후보 (핵심)
# ---------------------------
def build_candidates(gid):
    return [
        ("board", f"https://gall.dcinside.com/board/lists/?id={gid}"),
        ("mgallery", f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}"),
        ("mini", f"https://gall.dcinside.com/mini/board/lists/?id={gid}"),
        ("mobile", f"https://m.dcinside.com/board/{gid}")
    ]


# ---------------------------
# 유효 엔드포인트 탐색
# ---------------------------
def resolve_endpoint(gid):
    for gtype, url in build_candidates(gid):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")

            rows = soup.select("tr.ub-content")

            # mobile fallback
            if gtype == "mobile" and not rows:
                rows = soup.select("div.gall-detail-lst li")

            if len(rows) > 3:
                return gtype, url, soup

        except:
            continue

    return None, None, None


# ---------------------------
# 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1
    stop = False

    while page <= 80:
        url = f"{base_url}&page={page}"

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

        for row in rows:
            if is_filtered(row):
                continue

            dt = parse_post_date(row)
            if dt and dt < cutoff:
                stop = True
                continue

            nick = parse_writer(row)
            counter[nick] += 1

        if stop:
            break

        page += 1


# ---------------------------
# 갤러리 이름
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if meta:
        return meta.get("content", "").replace(
            " - 커뮤니티 포털 디시인사이드", ""
        ).strip()

    return "갤러리"


# ---------------------------
# MAIN
# ---------------------------
def crawl_gallery(user_url: str):
    user_url = normalize_url(user_url)

    gid = extract_gallery_id(user_url)
    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    now = datetime.now()

    # 7일 전 00시 기준
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    gtype, base_url, soup = resolve_endpoint(gid)

    if not base_url:
        raise Exception("갤러리 엔드포인트를 찾을 수 없음")

    gallery_name = get_gallery_name(soup)

    crawl_base(base_url, cutoff, counter)

    total = sum(counter.values())

    result = []
    for i, (nick, cnt) in enumerate(counter.most_common(), 1):
        result.append({
            "rank": i,
            "nickname": nick,
            "count": cnt,
            "share": round((cnt / total) * 100, 2) if total else 0
        })

    return {
        "gallery": gallery_name,
        "id": gid,
        "type": gtype,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }