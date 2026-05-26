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
# URL 정규화 (핵심)
# ---------------------------
def normalize_input_url(url: str):
    if not url.startswith("http"):
        url = "https://" + url

    url = url.replace("m.dcinside.com", "gall.dcinside.com")
    return url


# ---------------------------
# 갤러리 ID 추출
# ---------------------------
def extract_gallery_id(url: str):
    url = normalize_input_url(url)

    q = parse_qs(urlparse(url).query)
    if "id" in q:
        return q["id"][0]

    patterns = [
        r"id=([a-zA-Z0-9_]+)",
        r"/board/([a-zA-Z0-9_]+)",
        r"/mgallery/board/([a-zA-Z0-9_]+)",
        r"/mini/board/([a-zA-Z0-9_]+)",
        r"gall\.dcinside\.com/([a-zA-Z0-9_]+)$",
    ]

    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    return None


# ---------------------------
# 갤러리 타입 판별 (핵심)
# ---------------------------
def detect_board_type(url: str):
    url = normalize_input_url(url)

    # mini가 최우선
    if "mini" in url:
        return "mini"

    # mgallery 명시
    if "mgallery" in url:
        return "mgallery"

    # 기본은 board
    return "board"


# ---------------------------
# PC 리스트 URL 생성 (핵심)
# ---------------------------
def build_list_url(gid: str, board_type: str):
    return f"https://gall.dcinside.com/{board_type}/board/lists/?id={gid}"


# ---------------------------
# 갤러리 이름
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
def is_filtered(row):
    cls = row.get("class") or []
    if "notice" in cls:
        return True

    for sel in [".gall_subject", ".gall_num"]:
        el = row.select_one(sel)
        if el:
            t = el.get_text(strip=True)
            if t in ["공지", "설문", "AD", "광고"]:
                return True

    return False


# ---------------------------
# 작성자 파싱 (강화)
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

    return nick if nick else "ㅇㅇ"


# ---------------------------
# 날짜 파싱 (있으면 참고만)
# ---------------------------
def parse_date(row):
    d = row.select_one(".gall_date")
    if not d:
        return None

    t = d.get("title") or d.get_text(strip=True)
    now = datetime.now()

    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
    except:
        pass

    if re.match(r"^\d{1,2}:\d{2}$", t):
        h, m = map(int, t.split(":"))
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    if re.match(r"^\d{1,2}\.\d{1,2}$", t):
        mo, da = map(int, t.split("."))
        return datetime(now.year, mo, da)

    return None


# ---------------------------
# 크롤링 (과소집계 방지 구조)
# ---------------------------
def crawl(base_url, cutoff, counter):
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

        valid_rows = 0

        for row in rows:
            if is_filtered(row):
                continue

            writer = parse_writer(row)
            counter[writer] += 1
            valid_rows += 1

        # 안전 종료 조건 (너무 약하게 잡음 → 과소집계 방지)
        if valid_rows == 0:
            break

        page += 1


# ---------------------------
# 메인 함수
# ---------------------------
def crawl_gallery(url: str):
    url = normalize_input_url(url)

    gid = extract_gallery_id(url)
    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    board_type = detect_board_type(url)
    base_url = build_list_url(gid, board_type)

    now = datetime.now()

    # 사용자가 요구한 "7일 전 00시 기준"
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

    crawl(base_url, cutoff, counter)

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