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
# URL 정규화 (모바일 + 축약 대응)
# ---------------------------
def normalize_url(url: str):
    url = url.strip()

    if not url.startswith("http"):
        url = "https://" + url

    return url


# ---------------------------
# gallery id 추출 (모든 케이스 대응)
# ---------------------------
def extract_gallery_id(url: str):
    url = normalize_url(url)

    # 1) query id
    qs = parse_qs(urlparse(url).query)
    if "id" in qs:
        return qs["id"][0]

    # 2) path 기반 (/board/xxx, /mgallery/xxx, /mini/xxx)
    m = re.search(r"dcinside\.com/(?:board|mgallery|mini)/([a-zA-Z0-9_]+)", url)
    if m:
        return m.group(1)

    # 3) 모바일 (/board/xxx)
    m = re.search(r"m\.dcinside\.com/board/([a-zA-Z0-9_]+)", url)
    if m:
        return m.group(1)

    # 4) 최후: /xxx 단축 URL
    m = re.search(r"dcinside\.com/([a-zA-Z0-9_]+)$", url)
    if m:
        return m.group(1)

    return None


# ---------------------------
# 갤러리 타입 자동 판별
# ---------------------------
def detect_gallery_type(soup, gid):
    text = soup.get_text(" ", strip=True)

    if "미니 갤러리" in text:
        return "mini"

    if "마이너 갤러리" in text:
        return "mgallery"

    # 기본은 board
    return "board"


# ---------------------------
# base url 생성
# ---------------------------
def get_base_urls(gid):
    return {
        "board": [
            f"https://gall.dcinside.com/board/lists/?id={gid}"
        ],
        "mgallery": [
            f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}"
        ],
        "mini": [
            f"https://gall.dcinside.com/mini/board/lists/?id={gid}"
        ]
    }


# ---------------------------
# 갤러리 이름 파싱 개선
# ---------------------------
def get_gallery_name(soup):
    meta = soup.select_one('meta[name="title"]')
    if meta:
        title = meta.get("content", "")
        title = title.replace(" - 커뮤니티 포털 디시인사이드", "")
        return title.strip()

    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(strip=True)

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

    return None


# ---------------------------
# writer 파싱 개선 (undefined 해결)
# ---------------------------
def parse_writer(row):
    writer = row.select_one(".gall_writer") or row.select_one(".ub-writer")

    if not writer:
        return "ㅇㅇ"

    nick = (
        writer.get("data-nick")
        or writer.get_text(strip=True)
    )

    if not nick:
        return "ㅇㅇ"

    # dcinside 익명 처리
    if "ㅇㅇ" in nick:
        return "ㅇㅇ"

    return nick.strip()


# ---------------------------
# 크롤링
# ---------------------------
def crawl_base(base_url, cutoff, counter):
    page = 1
    stop = False

    while page <= 80:
        url = f"{base_url}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("tr.ub-content") or soup.select("tr")

        if not rows:
            break

        for row in rows:
            if is_filtered_row(row):
                continue

            dt = parse_post_date(row)
            if dt and dt < cutoff:
                stop = True
                continue

            nick = parse_writer(row)
            counter[nick] += 1

        if stop:
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

    now = datetime.now()

    # 🔥 핵심 수정: "7일 전 00시 기준"
    cutoff = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    counter = Counter()

    # 1차 페이지로 타입 감지
    base_guess = f"https://gall.dcinside.com/board/lists/?id={gid}"
    try:
        r = requests.get(base_guess, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        gtype = detect_gallery_type(soup, gid)
        gallery_name = get_gallery_name(soup)
    except:
        gtype = "board"
        gallery_name = gid

    base_urls = get_base_urls(gid)[gtype]

    for base_url in base_urls:
        try:
            crawl_base(base_url, cutoff, counter)
        except:
            continue

    total = sum(counter.values())

    result = []
    for i, (nick, cnt) in enumerate(counter.most_common(), 1):
        share = round((cnt / total) * 100, 2) if total else 0
        result.append({
            "rank": i,
            "nickname": nick,
            "count": cnt,
            "share": share
        })

    return {
        "gallery": gallery_name,
        "id": gid,
        "total": total,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result
    }