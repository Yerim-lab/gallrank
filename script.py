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
# gallery id 추출 (모바일/PC 통합)
# ---------------------------
def extract_gallery_id(url: str):
    parsed = urlparse(url)

    # 1) ?id=xxx (가장 정확)
    qs = parse_qs(parsed.query)
    if "id" in qs and qs["id"][0]:
        return qs["id"][0]

    path = parsed.path.strip("/")

    # 2) /board/lists?id=xxx 같은 구조 보강
    m = re.search(r"/board/lists/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    # 3) 루트형 (m.dcinside.com/krstock)
    if re.match(r"^[a-zA-Z0-9_]+$", path):
        return path

    # 4) 기존 구조 fallback
    m = re.search(r"/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", parsed.path)
    if m:
        return m.group(1)

    return None


# ---------------------------
# base url 생성
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
# 필터 (공지/설문/AD 제거)
# ---------------------------
def is_filtered_row(row):
    if "notice" in (row.get("class") or []):
        return True

    num = row.select_one(".gall_num")
    if num:
        t = num.get_text(strip=True)
        if t in ["공지", "설문", "AD", "광고"]:
            return True

    subject = row.select_one(".gall_subject")
    if subject:
        t = subject.get_text(strip=True)
        if t in ["공지", "설문", "AD", "광고"]:
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
# 페이지 크롤링
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
                continue  # 핵심 수정: 날짜 없는 글 제외

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

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    gid = extract_gallery_id(user_url)
    if not gid:
        raise ValueError("갤러리 ID 추출 실패 (URL 확인 필요)")

    now = datetime.now()
    cutoff = now - timedelta(days=7)

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

            crawl_base(base_url, cutoff, counter)

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