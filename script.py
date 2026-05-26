import re
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import urlparse

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
def normalize_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return url


# ---------------------------
# 실제 갤러리 타입 판별
# ---------------------------
def resolve_gallery(url: str):
    r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    final_url = r.url

    soup = BeautifulSoup(r.text, "lxml")

    path = urlparse(final_url).path

    if "/mini/" in path:
        gtype = "mini"
    elif "/mgallery/" in path:
        gtype = "mgallery"
    else:
        gtype = "board"

    # id 추출
    m = re.search(r"id=([a-zA-Z0-9_]+)", final_url)
    gid = m.group(1) if m else None

    if not gid:
        raise Exception("갤러리 ID 파싱 실패")

    return gid, gtype, soup


# ---------------------------
# base url 생성
# ---------------------------
def get_base_url(gid: str, gtype: str):
    return f"https://gall.dcinside.com/{gtype}/board/lists/?id={gid}"


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
# 필터
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
    date_el = row.select_one(".gall_date")
    if not date_el:
        return None

    title = date_el.get("title")
    if title:
        try:
            return datetime.strptime(title, "%Y-%m-%d %H:%M:%S")
        except:
            pass

    text = date_el.get_text(strip=True)
    now = datetime.now()

    if re.match(r"^\d{1,2}:\d{2}$", text):
        h, m = map(int, text.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    m = re.match(r"^(\d{1,2})\.(\d{1,2})$", text)
    if m:
        mo, d = map(int, m.groups())
        return datetime(now.year, mo, d)

    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", text)
    if m:
        y, mo, d = map(int, m.groups())
        return datetime(y, mo, d)

    return None


# ---------------------------
# writer 파싱 (핵심 수정)
# ---------------------------
def parse_writer(row):
    el = row.select_one(".gall_writer")

    if not el:
        el = row.select_one(".ub-writer")

    if not el:
        return "ㅇㅇ"

    nick = (
        el.get("data-nick")
        or el.get("data-user_nick")
        or el.get_text(strip=True)
        or "ㅇㅇ"
    )

    nick = nick.strip()

    return nick if nick else "ㅇㅇ"


# ---------------------------
# 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1
    stop = False

    while page <= 100:
        url = f"{base_url}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                break
        except:
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("tr.ub-content")

        if not rows:
            rows = soup.select("tr")

        if not rows:
            break

        for row in rows:
            if is_filtered_row(row):
                continue

            dt = parse_post_date(row)

            if dt and dt < cutoff:
                stop = True
                continue

            nickname = parse_writer(row)
            counter[nickname] += 1

        if stop:
            break

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    url = normalize_url(user_url)

    gid, gtype, soup = resolve_gallery(url)

    now = datetime.now()

    # 🔥 정확한 기준: 7일 전 "00:00"
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    base_url = get_base_url(gid, gtype)

    counter = Counter()
    gallery_name = get_gallery_name(soup)

    crawl_base(base_url, cutoff, counter)

    total = sum(counter.values())

    result = []
    rank = 1

    for nickname, count in counter.most_common():
        share = round((count / total) * 100, 2) if total else 0

        result.append({
            "rank": rank,
            "nickname": nickname,
            "count": count,
            "share": share
        })

        rank += 1

    return {
        "gallery": gallery_name,
        "type": gtype,
        "gid": gid,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }