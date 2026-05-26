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
# gallery id 추출
# ---------------------------
def extract_gallery_id(url: str):
    patterns = [
        r"[?&]id=([a-zA-Z0-9_]+)",
        r"m\.dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)",
        r"dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)",
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# ---------------------------
# 3개 타입 전부 크롤링
# ---------------------------
def get_base_urls(gid: str):
    return [
        f"https://gall.dcinside.com/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mini/board/lists/?id={gid}",
    ]


# ---------------------------
# gallery name
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if not meta:
        return "갤러리"

    return meta.get("content", "").replace(
        " - 커뮤니티 포털 디시인사이드", ""
    ).strip()


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
# 날짜 파싱 (title 우선)
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
# 페이지 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter, now):
    page = 1
    stop = False

    while True:
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
            rows = soup.select("tr")

        if not rows:
            break

        for row in rows:
            if is_filtered_row(row):
                continue

            post_date = parse_post_date(row)

            if post_date and post_date < cutoff:
                stop = True
                continue

            writer = row.select_one(".gall_writer") or row.select_one(".ub-writer")

            if writer:
                nickname = (
                    writer.get("data-nick")
                    or writer.get_text(strip=True)
                    or "ㅇㅇ"
                ).strip()
            else:
                nickname = "ㅇㅇ"

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

        if stop:
            break

        page += 1

        if page > 100:
            break


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    gid = extract_gallery_id(user_url)
    if not gid:
        raise Exception("갤러리 ID를 찾을 수 없음")

    now = datetime.now()
    cutoff = (now - timedelta(days=7)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )

    counter = Counter()
    gallery_name = gid

    base_urls = get_base_urls(gid)

    for base_url in base_urls:
        try:
            r = requests.get(base_url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")

            if gallery_name == gid:
                gallery_name = get_gallery_name(soup)

            crawl_base(base_url, cutoff, counter, now)

        except:
            continue

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