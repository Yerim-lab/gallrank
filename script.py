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


# ---------------------------
# URL → gallery id
# ---------------------------
def extract_gallery_id(url: str):
    match = re.search(r"[?&]id=([a-zA-Z0-9_]+)", url)
    if match:
        return match.group(1)

    match = re.search(r"m\.dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", url)
    if match:
        return match.group(1)

    match = re.search(r"dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", url)
    if match:
        return match.group(1)

    return None


# ---------------------------
# base url 찾기
# ---------------------------
def build_candidate_urls(gid: str):
    return [
        f"https://gall.dcinside.com/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mini/board/lists/?id={gid}",
    ]


def find_working_url(gid: str):
    for url in build_candidate_urls(gid):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            if soup.select_one("tr.ub-content"):
                return url
        except:
            continue

    return None


# ---------------------------
# gallery name
# ---------------------------
def get_gallery_name(soup: BeautifulSoup):
    meta = soup.select_one('meta[name="title"]')
    if not meta:
        return "갤러리"

    title = meta.get("content", "")
    return title.replace(" - 커뮤니티 포털 디시인사이드", "").strip()


# ---------------------------
# row filter
# ---------------------------
def is_filtered_row(row) -> bool:
    if "notice" in (row.get("class") or []):
        return True

    num = row.select_one(".gall_num")
    if num:
        if num.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
            return True

    subject = row.select_one(".gall_subject")
    if subject:
        if subject.get_text(strip=True) in ["공지", "설문", "AD", "광고"]:
            return True

    return False


# ---------------------------
# 날짜 파싱 (DCInside 대응)
# ---------------------------
def parse_post_date(row, base_datetime: datetime):
    """
    DCInside 날짜 형식:
    - 05.26
    - 2026.05.26
    - 12:34 (오늘)
    """

    date_el = row.select_one(".gall_date")
    if not date_el:
        return None

    text = date_el.get_text(strip=True)

    now = base_datetime

    # 시간형 (오늘)
    if re.match(r"^\d{1,2}:\d{2}$", text):
        try:
            h, m = map(int, text.split(":"))
            return now.replace(hour=h, minute=m, second=0, microsecond=0)
        except:
            return None

    # MM.DD
    m = re.match(r"^(\d{1,2})\.(\d{1,2})$", text)
    if m:
        month, day = map(int, m.groups())
        year = now.year
        return datetime(year, month, day)

    # YYYY.MM.DD
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", text)
    if m:
        y, mth, d = map(int, m.groups())
        return datetime(y, mth, d)

    return None


# ---------------------------
# main crawler
# ---------------------------
def crawl_gallery(user_url: str):
    gid = extract_gallery_id(user_url)
    if not gid:
        raise Exception("갤러리 ID를 찾을 수 없음")

    base_url = find_working_url(gid)
    if not base_url:
        raise Exception("갤러리를 찾을 수 없음")

    # ---------------------------
    # cutoff: 오늘 기준 7일 전 23:59:59
    # ---------------------------
    now = datetime.now()
    cutoff = (now - timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=0)

    counter = Counter()
    page = 1
    gallery_name = gid

    while True:
        url = f"{base_url}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")

        if page == 1:
            gallery_name = get_gallery_name(soup)

        rows = soup.select("tr.ub-content")
        if not rows:
            break

        stop = False

        for row in rows:
            if is_filtered_row(row):
                continue

            post_date = parse_post_date(row, now)
            if post_date and post_date < cutoff:
                stop = True
                continue

            writer = row.select_one(".gall_writer")
            if not writer:
                continue

            nickname = (
                writer.get("data-nick")
                or writer.get_text(strip=True)
                or "ㅇㅇ"
            ).strip()

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

        if stop:
            break

        page += 1

        if page > 50:
            break

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
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }