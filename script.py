import re
import requests

from bs4 import BeautifulSoup
from collections import Counter


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    )
}


def extract_gallery_id(url):

    match = re.search(
        r"id=([a-zA-Z0-9_]+)",
        url
    )

    if match:
        return match.group(1)

    match = re.search(
        r"dcinside\\.com/([a-zA-Z0-9_]+)",
        url
    )

    if match:

        gid = match.group(1)

        blocked = [
            "board",
            "mini",
            "mgallery"
        ]

        if gid not in blocked:
            return gid

    return None


def get_candidate_urls(gid):

    return [

        f"https://gall.dcinside.com/board/lists/?id={gid}",

        f"https://gall.dcinside.com/mgallery/board/lists/?id={gid}",

        f"https://gall.dcinside.com/mini/board/lists/?id={gid}"

    ]


def find_gallery_url(gid):

    urls = get_candidate_urls(gid)

    for url in urls:

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(
                response.text,
                "lxml"
            )

            rows = soup.select(
                "tr.ub-content"
            )

            if rows:
                return url

        except:
            continue

    return None


def get_gallery_name(soup):

    meta_title = soup.select_one(
        'meta[name="title"]'
    )

    if not meta_title:
        return "갤러리"

    content = meta_title.get(
        "content",
        ""
    ).strip()

    content = (
        content
        .replace(
            " - 커뮤니티 포털 디시인사이드",
            ""
        )
        .strip()
    )

    return content


def crawl_gallery(user_url):

    gid = extract_gallery_id(user_url)

    if not gid:
        raise Exception("갤러리 ID 추출 실패")

    base_url = find_gallery_url(gid)

    if not base_url:
        raise Exception("갤러리를 찾을 수 없음")

    counter = Counter()

    gallery_name = gid

    page = 1

    while True:

        url = f"{base_url}&page={page}"

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

        except:
            break

        if response.status_code != 200:
            break

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        if page == 1:
            gallery_name = get_gallery_name(soup)

        rows = soup.select(
            "tr.ub-content"
        )

        if not rows:
            break

        valid_count = 0

        for row in rows:

            if "notice" in row.get(
                "class",
                []
            ):
                continue

            writer = row.select_one(
                ".gall_writer"
            )

            if not writer:
                continue

            nickname = (
                writer.get("data-nick")
                or writer.text.strip()
                or "ㅇㅇ"
            )

            nickname = nickname.strip()

            if not nickname:
                nickname = "ㅇㅇ"

            counter[nickname] += 1

            valid_count += 1

        if valid_count == 0:
            break

        page += 1

        if page > 15:
            break

    total = sum(counter.values())

    result = []

    rank = 1

    for nickname, count in counter.most_common():

        share = round(
            (count / total) * 100,
            2
        )

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