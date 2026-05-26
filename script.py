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
    ),
    "Referer": "https://gall.dcinside.com/"
}


def parse_url(url):
    url = url.strip()

    # 마이너 갤러리
    if "mgallery" in url:
        match = re.search(r"id=([a-zA-Z0-9_]+)", url)

        if match:
            return {
                "type": "mgallery",
                "id": match.group(1)
            }

    # 미니 갤러리
    if "mini" in url:
        match = re.search(r"id=([a-zA-Z0-9_]+)", url)

        if match:
            return {
                "type": "mini",
                "id": match.group(1)
            }

    # 일반 갤러리 lists
    if "board/lists" in url:
        match = re.search(r"id=([a-zA-Z0-9_]+)", url)

        if match:
            return {
                "type": "board",
                "id": match.group(1)
            }

    # 숏 URL
    match = re.search(
        r"dcinside\.com/([a-zA-Z0-9_]+)",
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
            return {
                "type": "auto",
                "id": gid
            }

    return None


def build_urls(gallery_id):
    return [
        (
            "https://gall.dcinside.com/"
            f"board/lists/?id={gallery_id}"
        ),

        (
            "https://gall.dcinside.com/"
            f"mgallery/board/lists/?id={gallery_id}"
        ),

        (
            "https://gall.dcinside.com/"
            f"mini/board/lists/?id={gallery_id}"
        )
    ]


def request_gallery(url, page):
    full_url = f"{url}&page={page}"

    response = requests.get(
        full_url,
        headers=HEADERS,
        timeout=15
    )

    print("REQUEST:", full_url)
    print("STATUS:", response.status_code)

    if response.status_code != 200:
        return None

    return response


def find_working_gallery(gallery_id):
    urls = build_urls(gallery_id)

    for url in urls:
        response = request_gallery(url, 1)

        if not response:
            continue

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        rows = soup.select("tr.ub-content")

        if rows:
            print("WORKING URL:", url)
            return url

    return None


def crawl_gallery(user_url):
    parsed = parse_url(user_url)

    if not parsed:
        raise Exception(
            "URL 파싱 실패"
        )

    gallery_id = parsed["id"]

    working_url = find_working_gallery(
        gallery_id
    )

    if not working_url:
        raise Exception(
            "갤러리를 찾을 수 없음"
        )

    counter = Counter()

    gallery_name = ""

    page = 1

    while True:
        response = request_gallery(
            working_url,
            page
        )

        if not response:
            break

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        if not gallery_name:
            title = soup.select_one(
                ".title_subject"
            )

            if title:
                gallery_name = (
                    title.text.strip()
                )
            else:
                gallery_name = gallery_id

        rows = soup.select(
            "tr.ub-content"
        )

        if not rows:
            break

        post_found = False

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

            post_found = True

        if not post_found:
            break

        page += 1

        if page > 20:
            break

    total = sum(counter.values())

    result = []

    rank = 1

    for nickname, count in (
        counter.most_common()
    ):
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