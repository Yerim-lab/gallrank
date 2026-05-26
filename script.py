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
# 1. URL 정규화 (앱/복사 링크 대응)
# ---------------------------
def normalize_url(url: str):
    url = url.strip()

    if url.startswith("http://") or url.startswith("https://"):
        return url

    if url.startswith("//"):
        return "https:" + url

    if "dcinside.com" in url:
        return "https://" + url

    return url


# ---------------------------
# 2. resolve + type/id 추출
# ---------------------------
def resolve_dcinside(url: str):
    url = normalize_url(url)

    r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    final_url = r.url

    parsed = urlparse(final_url)

    qs = parse_qs(parsed.query)
    gid = qs.get("id", [None])[0]

    path = parsed.path.strip("/")

    if not gid:
        parts = path.split("/")
        gid = parts[-1] if parts else None

    if "/mini/" in parsed.path:
        gtype = "mini"
    elif "/mgallery/" in parsed.path:
        gtype = "mgallery"
    else:
        gtype = "board"

    return gtype, gid, final_url


# ---------------------------
# 3. base url 생성 (단일 경로)
# ---------------------------
def build_base_url(gtype, gid):
    if not gid:
        return None

    if gtype == "mini":
        return f"https://gall.dcinside.com/mini/board/lists/?id={gid}"
    elif gtype == "mgallery":
        return f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}"
    else:
        return f"https://gall.dcinside.com/board/lists/?id={gid}"


# ---------------------------
# 4. 필터 (공지/AD/설문 제거)
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
# 5. 날짜 파싱 (DCInside 전체 대응)
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
# 6. 크롤링 엔진
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

            # 핵심: 날짜 없는 글은 완전 제외
            if not post_date:
                continue

            cutoff = cutoff

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
# 7. main
# ---------------------------
def crawl_gallery(url: str):
    gtype, gid, final_url = resolve_dcinside(url)

    if not gid:
        raise ValueError("갤러리 ID 추출 실패")

    base_url = build_base_url(gtype, gid)
    if not base_url:
        raise ValueError("base URL 생성 실패")

    now = datetime.now()
    cutoff = now - timedelta(days=7)

    counter = Counter()

    crawl_base(base_url, cutoff, counter)

    total = sum(counter.values())

    result = []
    rank = 1

    for nickname, count in counter.most_common():
        result.append({
            "rank": rank,
            "nickname": nickname,
            "count": count,
            "share": round(count / total * 100, 2) if total else 0
        })
        rank += 1

    return {
        "type": gtype,
        "gallery": gid,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }