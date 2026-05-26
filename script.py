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


def extract_gallery_id(url: str):

    match = re.search(r"id=([a-zA-Z0-9_]+)", url)
    if match:
        return match.group(1)

    match = re.search(r"dcinside\.com/([a-zA-Z0-9_]+)", url)
    if match:
        gid = match.group(1)

        if gid not in ["board", "mgallery", "mini"]:
            return gid

    return None


def build_candidate_urls(gid: str):

    return [
        f"https://gall.dcinside.com/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}",
        f"https://gall.dcinside.com/mini/board/lists/?id={gid}",
    ]


def find_working_url(gid: str):

    for url in build_candidate_urls(gid):

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")

            if soup.select_one("tr.ub-content"):
                return url

        except:
            continue

    return None


def get_gallery_name(soup: BeautifulSoup):

    meta = soup.select_one('meta[name="title"]')

    if not meta:
        return "갤러리"

    title = meta.get("content", "").strip()

    title = title.replace(
        " - 커뮤니티 포털 디시인사이드",
        ""
    ).strip()

    return title


def crawl_gallery(user_url: str):

    gid = extract_gallery_id(user_url)

    if not gid:
        raise Exception("갤러리 ID를 찾을 수 없음")

    base_url = find_working_url(gid)

    if not base_url:
        raise Exception("갤러리를 찾을 수 없음")

    counter = Counter()
    gallery_name = gid

    page = 1

    while True:

        url = f"{base_url}&page={page}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
        except:
            break

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "lxml")

        if page == 1:
            gallery_name = get_gallery_name(soup)

        rows = soup.select("tr.ub-content")

        if not rows:
            break

        valid_count = 0

        for row in rows:

            # 공지 제외
            if "notice" in row.get("class", []):
                continue

            # 제목 분류 (설문 / AD / 공지 제외)
            subject = row.select_one(".gall_subject")

            if subject:
                text = subject.get_text(strip=True)

                if text in ["공지", "설문", "AD"]:
                    continue

            writer = row.select_one(".gall_writer")

            if not writer:
                continue

            nickname = (
                writer.get("data-nick")
                or writer.get_text(strip=True)
                or "ㅇㅇ"
            ).strip()

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1
            valid_count += 1

        if valid_count == 0:
            break

        page += 1

        if page > 20:
            break

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
        "result": result
    }