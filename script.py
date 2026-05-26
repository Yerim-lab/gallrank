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
# URL 정규화 + 갤러리 ID 추출
# ---------------------------
def normalize_url(url: str):
    if not url.startswith("http"):
        url = "https://" + url

    url = url.replace("m.dcinside.com", "gall.dcinside.com")
    return url


def extract_gallery_id(url: str):
    url = normalize_url(url)

    # query param
    q = parse_qs(urlparse(url).query)
    if "id" in q:
        return q["id"][0]

    # path patterns
    patterns = [
        r"gall\.dcinside\.com/(?:board|mgallery|mini)/lists/\?id=([a-zA-Z0-9_]+)",
        r"gall\.dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)",
        r"gall\.dcinside\.com/([a-zA-Z0-9_]+)$",
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# ---------------------------
# 갤러리 타입 강제 판별 (핵심 수정)
# ---------------------------
def detect_board_type(url: str):
    url = normalize_url(url)

    if "/mini/" in url:
        return "mini"
    if "/mgallery/" in url:
        return "mgallery"
    return "board"


def get_base_url(gid: str, board_type: str):
    return f"https://gall.dcinside.com/{board_type}/board/lists/?id={gid}"


# ---------------------------
# 갤러리 이름
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if not meta:
        return "갤러리"

    title = meta.get("content", "")
    return title.replace(" - 커뮤니티 포털 디시인사이드", "").strip()


# ---------------------------
# 필터
# ---------------------------
def is_filtered_row(row):
    cls = row.get("class") or []
    if "notice" in cls:
        return True

    subject = row.select_one(".gall_subject")
    if subject:
        t = subject.get_text(strip=True)
        if t in ["공지", "설문", "AD", "광고"]:
            return True

    num = row.select_one(".gall_num")
    if num:
        t = num.get_text(strip=True)
        if t in ["공지", "설문", "AD", "광고"]:
            return True

    return False


# ---------------------------
# 날짜 파싱 (없으면 None 허용)
# ---------------------------
def parse_post_date(row):
    el = row.select_one(".gall_date")
    if not el:
        return None

    t = el.get("title") or el.get_text(strip=True)
    now = datetime.now()

    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
    except:
        pass

    if re.match(r"^\d{1,2}:\d{2}$", t):
        h, m = map(int, t.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    if re.match(r"^\d{1,2}\.\d{1,2}$", t):
        mo, d = map(int, t.split("."))
        return datetime(now.year, mo, d)

    return None


# ---------------------------
# writer 파싱 (핵심 개선)
# ---------------------------
def parse_writer(row):
    w = row.select_one(".gall_writer") or row.select_one(".ub-writer")

    if not w:
        return "ㅇㅇ"

    nick = (
        w.get("data-nick")
        or w.get("data-name")
        or w.get_text(strip=True)
        or "ㅇㅇ"
    ).strip()

    if not nick:
        return "ㅇㅇ"

    return nick


# ---------------------------
# 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1
    max_page = 200

    while page <= max_page:
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

        empty_count = 0

        for row in rows:
            if is_filtered_row(row):
                continue

            writer = parse_writer(row)
            counter[writer] += 1

            # cutoff는 "중단"이 아니라 그냥 참고만
            dt = parse_post_date(row)
            if dt and dt < cutoff:
                empty_count += 1

        # 너무 오래된 페이지만 있으면 종료
        if empty_count > len(rows) * 0.7:
            break

        page += 1


# ---------------------------
# main
# ---------------------------
def crawl_gallery(user_url: str):
    user_url = normalize_url(user_url)

    gid = extract_gallery_id(user_url)
    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    board_type = detect_board_type(user_url)

    now = datetime.now()
    cutoff = now - timedelta(days=7)

    base_url = get_base_url(gid, board_type)

    counter = Counter()

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
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }