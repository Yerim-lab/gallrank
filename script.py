import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta

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


# ---------------------------
# URL → ID 추출 (축약 포함)
# ---------------------------
def extract_gallery_id(url: str):
    url = url.strip()

    if not url.startswith("http"):
        url = "https://" + url

    patterns = [
        r"[?&]id=([a-zA-Z0-9_]+)",
        r"gall\.dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)",
        r"gall\.dcinside\.com/([a-zA-Z0-9_]+)$",
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# ---------------------------
# 갤러리 타입 자동 탐색 (핵심)
# ---------------------------
def detect_gallery_type(gid: str):
    for t in ["mgallery", "board", "mini"]:
        url = BASE[t].format(gid=gid)

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            continue

        if r.status_code != 200:
            continue

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("tr.ub-content")

        if rows:
            return t, url

    return None, None


# ---------------------------
# 갤러리 이름 추출 (정확 버전)
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')

    if meta:
        content = meta.get("content", "")
        return content.split(" - ")[0].strip()

    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)

    return "갤러리"


# ---------------------------
# 필터 (공지 / 설문 / 광고 제거)
# ---------------------------
def is_filtered_row(row):
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
# 날짜 파싱
# ---------------------------
def parse_post_date(row):
    el = row.select_one(".gall_date")
    if not el:
        return None

    t = el.get("title")
    if t:
        try:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except:
            pass

    txt = el.get_text(strip=True)
    now = datetime.now()

    if re.match(r"^\d{1,2}:\d{2}$", txt):
        h, m = map(int, txt.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    m = re.match(r"^(\d{1,2})\.(\d{1,2})$", txt)
    if m:
        mo, d = map(int, m.groups())
        return datetime(now.year, mo, d)

    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", txt)
    if m:
        y, mo, d = map(int, m.groups())
        return datetime(y, mo, d)

    return None


# ---------------------------
# 크롤링 엔진
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1

    while page <= 100:
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

        stop = False

        for row in rows:
            if is_filtered_row(row):
                continue

            dt = parse_post_date(row)

            if dt and dt < cutoff:
                stop = True
                continue

            writer = row.select_one(".gall_writer") or row.select_one(".ub-writer")

            if writer:
                nick = (
                    writer.get("data-nick")
                    or writer.get_text(strip=True)
                    or "ㅇㅇ"
                ).strip()
            else:
                nick = "ㅇㅇ"

            if not nick:
                nick = "ㅇㅇ"

            counter[nick] += 1

        if stop:
            break

        page += 1


# ---------------------------
# 메인
# ---------------------------
def crawl_gallery(user_url: str):
    gid = extract_gallery_id(user_url)
    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    now = datetime.now()

    # 7일 전 00:00 기준
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    gtype, base_url = detect_gallery_type(gid)
    if not base_url:
        raise Exception("갤러리 타입 판별 실패")

    # 이름은 확정된 URL 기준으로 재조회
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        gallery_name = get_gallery_name(soup)
    except:
        gallery_name = gid

    crawl_base(base_url, cutoff, counter)

    total = sum(counter.values())

    result = []
    for i, (nick, cnt) in enumerate(counter.most_common(), 1):
        result.append({
            "rank": i,
            "nickname": nick,
            "count": cnt,
            "share": round(cnt / total * 100, 2) if total else 0
        })

    return {
        "gallery": gallery_name,
        "type": gtype,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }