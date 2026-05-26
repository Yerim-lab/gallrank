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
# URL 최종 리다이렉트 해석
# ---------------------------
def resolve_final_url(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.url, r.text
    except:
        return url, None


# ---------------------------
# gallery id 추출 (최종 URL 기준)
# ---------------------------
def extract_gallery_id(url: str):
    parsed = urlparse(url)

    qs = parse_qs(parsed.query)
    if "id" in qs and qs["id"][0]:
        return qs["id"][0]

    path = parsed.path.strip("/")

    # /board/lists?id=xxx fallback
    if parsed.path:
        m = re.search(r"[?&]id=([a-zA-Z0-9_]+)", url)
        if m:
            return m.group(1)

    # /krstock 같은 slug형
    if path and "/" not in path:
        return path

    # /board/mgallery 구조
    m = re.search(r"/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    return None


# ---------------------------
# base urls
# ---------------------------
def get_base_urls(gid: str):
    return [
        f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
        f"https://gall.dcinside.com/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mini/board/lists/?id={gid}",
    ]


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
# 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1

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
            break

        for row in rows:
            if is_filtered_row(row):
                continue

            post_date = parse_post_date(row)
            if not post_date:
                continue

            if post_date < cutoff:
                continue

            writer = row.select_one(".gall_writer") or row.select_one(".ub-writer")

            if writer:
                nickname = (
                    writer.get("data-nick")
                    or writer.get_text(strip=True)
                ).strip()
            else:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    final_url, html = resolve_final_url(user_url)

    gid = extract_gallery_id(final_url)
    if not gid:
        raise ValueError("갤러리 ID 추출 실패 (리다이렉트 후 URL 확인 필요)")

    now = datetime.now()
    cutoff = now - timedelta(days=7)

    counter = Counter()

    # base urls
    base_urls = get_base_urls(gid)

    # gallery name (최종 HTML에서 추출)
    gallery_name = gid
    if html:
        soup = BeautifulSoup(html, "lxml")
        meta = soup.select_one('meta[name="title"]')
        if meta:
            gallery_name = meta.get("content", "").replace(
                " - 커뮤니티 포털 디시인사이드", ""
            ).strip() or gid

    for base_url in base_urls:
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
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }