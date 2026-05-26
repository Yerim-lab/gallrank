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
# URL resolve + type/id 추출
# ---------------------------
def resolve_and_parse(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        final_url = r.url
        html = r.text
    except:
        final_url = url
        html = None

    parsed = urlparse(final_url)

    qs = parse_qs(parsed.query)
    gid = None

    if "id" in qs and qs["id"][0]:
        gid = qs["id"][0]
    else:
        path = parsed.path.strip("/")

        # mini/xxx
        if path.startswith("mini/"):
            gid = path.split("/")[1]
        else:
            gid = path.split("/")[0] if path else None

    # type 판별
    if "/mini/" in parsed.path:
        gtype = "mini"
    elif "/mgallery/" in parsed.path:
        gtype = "mgallery"
    else:
        # 축약 URL fallback (krstock 같은 경우 mgallery로 수렴)
        if "krstock" in final_url:
            gtype = "mgallery"
        else:
            gtype = "board"

    return final_url, html, gtype, gid


# ---------------------------
# base url 생성 (단일)
# ---------------------------
def get_base_url(gtype, gid):
    if not gid:
        return None

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

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    final_url, html, gtype, gid = resolve_and_parse(user_url)

    if not gid:
        raise ValueError("갤러리 ID 추출 실패")

    base_url = get_base_url(gtype, gid)
    if not base_url:
        raise ValueError("base_url 생성 실패")

    counter = Counter()

    now = datetime.now()
    cutoff = now - timedelta(days=7)

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