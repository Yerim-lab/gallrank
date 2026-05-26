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
# URL normalize
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
# resolve + gallery type
# ---------------------------
def resolve_dcinside(url: str):
    url = normalize_url(url)

    r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    final_url = r.url

    parsed = urlparse(final_url)

    qs = parse_qs(parsed.query)
    gid = qs.get("id", [None])[0]

    if not gid:
        gid = parsed.path.strip("/").split("/")[-1]

    path = parsed.path

    if "/mini/" in path:
        gtype = "mini"
    elif "/mgallery/" in path:
        gtype = "mgallery"
    else:
        gtype = "board"

    # 축약 갤러리 보정 (DC 구조 특성)
    if "krstock" in final_url:
        gtype = "mgallery"

    return gtype, gid, final_url


# ---------------------------
# base url
# ---------------------------
def build_base_url(gtype, gid):
    if gtype == "mini":
        return f"https://gall.dcinside.com/mini/board/lists/?id={gid}"
    elif gtype == "mgallery":
        return f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}"
    else:
        return f"https://gall.dcinside.com/board/lists/?id={gid}"


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
# 핵심: 유저 식별 로직 (FIX POINT)
# ---------------------------
def extract_user_key(writer):
    if not writer:
        return "ㅇㅇ"

    nick = writer.get("data-nick") or writer.get_text(strip=True) or "ㅇㅇ"
    uid = writer.get("data-user_id") or writer.get("data-uid") or ""

    nick = nick.strip()

    # uid가 있으면 절대 이걸 기준으로 묶어야 함
    if uid:
        return f"{nick}({uid})"

    return nick


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

            key = extract_user_key(writer)
            counter[key] += 1

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(url: str):
    gtype, gid, final_url = resolve_dcinside(url)

    if not gid:
        raise ValueError("갤러리 ID 추출 실패")

    base_url = build_base_url(gtype, gid)

    now = datetime.now()

    # 7일 전 00시 기준
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    crawl_base(base_url, cutoff, counter)

    total = sum(counter.values())

    result = []
    rank = 1

    for user, count in counter.most_common():
        result.append({
            "rank": rank,
            "user": user,
            "count": count,
            "share": round(count / total * 100, 2) if total else 0
        })
        rank += 1

    return {
        "type": gtype,
        "gallery": gid,
        "final_url": final_url,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "result": result
    }