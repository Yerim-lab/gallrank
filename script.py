import re
import requests

from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

BASE = {
    "board": "https://gall.dcinside.com/board/lists/?id={gid}",
    "mgallery": "https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
    "mini": "https://gall.dcinside.com/mini/board/lists/?id={gid}",
}


def resolve_url(url: str):

    url = url.strip()

    if not url.startswith("http"):
        url = "https://" + url

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
            allow_redirects=True
        )

        return r.url

    except:
        return url


def extract_gid(url: str):

    url = resolve_url(url)

    m = re.search(r"id=([a-zA-Z0-9_]+)", url)

    if m:
        return m.group(1)

    return None


def is_mini_url(url: str):

    return "/mini/" in url


def is_valid_gallery_page(html: str):

    soup = BeautifulSoup(html, "lxml")

    return bool(
        soup.select_one("tr.ub-content")
        or soup.select_one(".gall_listwrap")
        or soup.select_one(".gall_tit")
    )


def detect_gallery_type(user_url: str):

    url = resolve_url(user_url)

    gid = extract_gid(url)

    if not gid:
        return None, None

    # 미니는 URL 기준 우선 판별
    if is_mini_url(url):
        return "mini", BASE["mini"].format(gid=gid)

    # 마갤 -> 정식갤 순서
    for gtype in ["mgallery", "board"]:

        test_url = BASE[gtype].format(gid=gid)

        try:
            r = requests.get(
                test_url,
                headers=HEADERS,
                timeout=10
            )

        except:
            continue

        if r.status_code != 200:
            continue

        if is_valid_gallery_page(r.text):
            return gtype, test_url

    return None, None


def is_filtered_row(row):

    classes = row.get("class") or []

    # notice 클래스
    if "notice" in classes:
        return True

    # 번호칸 검사
    num = row.select_one(".gall_num")

    if num:

        text = num.get_text(strip=True)

        if text in ["공지", "설문", "AD", "광고"]:
            return True

    # 말머리 검사
    subject = row.select_one(".gall_subject")

    if subject:

        text = subject.get_text(strip=True)

        if text in ["공지", "설문", "AD", "광고"]:
            return True

    return False


def get_writer(row):

    addbox = row.select_one("div.addbox")

    if not addbox:
        return "오류값"

    nick_el = addbox.select_one("span.nickname")

    if not nick_el:
        return "오류값"

    classes = nick_el.get("class", [])

    # title 우선
    nick = nick_el.get("title", "").strip()

    # em fallback
    if not nick:

        em = nick_el.select_one("em")

        if em:
            nick = em.get_text(strip=True)

    # 최종 fallback
    if not nick:
        nick = nick_el.get_text(strip=True)

    nick = nick.strip()

    if not nick:
        return "오류값"

    # 고닉 / 반고닉
    if "in" in classes:
        return nick

    # 유동
    ip = ""

    ip_el = addbox.select_one("span.ip")

    if ip_el:
        ip = ip_el.get_text(strip=True).strip()

    if ip:
        return f"{nick}{ip}"

    return nick


def get_gallery_name(soup):

    meta = soup.select_one('meta[name="title"]')

    if meta:

        content = meta.get("content", "").strip()

        if content:
            return content.split(" - ")[0].strip()

    h1 = soup.select_one("h1")

    if h1:

        text = h1.get_text(strip=True)

        if text:
            return text

    return "갤러리"


def crawl_base(base_url, counter):

    page = 1

    while page <= 1000:

        url = f"{base_url}&page={page}"

        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")

        rows = soup.select("tr.ub-content")

        if not rows:
            break

        for row in rows:

            if is_filtered_row(row):
                continue

            nick = get_writer(row)

            if nick == "오류값":
                continue

            counter[nick] += 1

        page += 1


def crawl_gallery(user_url: str):

    gtype, base_url = detect_gallery_type(user_url)

    if not base_url:
        raise Exception("갤러리 타입 판별 실패")

    counter = Counter()

    try:
        r = requests.get(
            base_url,
            headers=HEADERS,
            timeout=10
        )

        soup = BeautifulSoup(r.text, "lxml")

        gallery_name = get_gallery_name(soup)

    except:
        gallery_name = extract_gid(user_url) or "갤러리"

    crawl_base(base_url, counter)

    total = sum(counter.values())

    result = []

    for rank, (nick, count) in enumerate(
        counter.most_common(),
        start=1
    ):

        share = 0

        if total:
            share = round(count / total * 100, 2)

        result.append({
            "rank": rank,
            "nickname": nick,
            "count": count,
            "share": share
        })

    return {
        "gallery": gallery_name,
        "type": gtype,
        "total": total,
        "pages": 100,
        "result": result
    }