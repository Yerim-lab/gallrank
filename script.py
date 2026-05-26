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
# URL 리다이렉트 해결
# ---------------------------
def resolve_url(url: str):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.url
    except:
        return url


# ---------------------------
# 갤러리 ID 추출
# ---------------------------
def extract_gid(url: str):
    url = resolve_url(url)
    m = re.search(r"id=([a-zA-Z0-9_]+)", url)
    return m.group(1) if m else None


# ---------------------------
# DCInside "진짜 리스트 페이지" 판별
# ---------------------------
def is_valid_gallery_page(html: str):
    soup = BeautifulSoup(html, "lxml")

    # 핵심: 게시글 row 존재 여부
    if soup.select_one("tr.ub-content"):
        return True

    return False


# ---------------------------
# 갤러리 타입 탐지 (probe only)
# ---------------------------
def detect_gallery_type(gid: str):
    for t in ["mini", "mgallery", "board"]:
        url = BASE[t].format(gid=gid)

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            continue

        if r.status_code != 200:
            continue

        if is_valid_gallery_page(r.text):
            return t, url

    return None, None


# ---------------------------
# 갤러리 이름 추출
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if meta:
        return meta.get("content", "").split(" - ")[0].strip()

    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)

    return "갤러리"


# ---------------------------
# 필터
# ---------------------------
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


# ---------------------------
# 날짜 파싱
# ---------------------------
def parse_post_date(row):
    el = row.select_one(".gall_date")
    if not el:
        return None

    t = el.get("title")
    now = datetime.now()

    if t:
        try:
            return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except:
            pass

    txt = el.get_text(strip=True)

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
# 크롤링
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

        page_has_in_range = False

        for row in rows:
            if is_filtered_row(row):
                continue

            dt = parse_post_date(row)
            in_range = True if dt is None else (dt >= cutoff)

            if in_range:
                page_has_in_range = True

                writer = row.select_one(".gall_writer") or row.select_one(".ub-writer")

                nick = "ㅇㅇ"
                if writer:
                    nick = (
                        writer.get("data-nick")
                        or writer.get_text(strip=True)
                        or "ㅇㅇ"
                    ).strip() or "ㅇㅇ"

                counter[nick] += 1

        if not page_has_in_range:
            break

        page += 1


# ---------------------------
# 메인
# ---------------------------
def crawl_gallery(user_url: str):
    gid = extract_gid(user_url)

    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    gtype, base_url = detect_gallery_type(gid)

    if not base_url:
        raise Exception("갤러리 타입 판별 실패")

    now = datetime.now()
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        gallery_name = get_gallery_name(soup)
    except:
        gallery_name = gid

    crawl_base(base_url, cutoff, counter)

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
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }