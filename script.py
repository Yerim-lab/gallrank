import re
import requests

from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36"
    )
}


def extract_gallery_id(url):
    url = url.strip()

    # id=xxx 우선 추출
    m = re.search(r"id=([a-zA-Z0-9_]+)", url)

    if m:
        return m.group(1)

    # 숏 URL 처리
    m = re.search(
        r"dcinside\.com/([a-zA-Z0-9_]+)",
        url
    )

    if m:
        gid = m.group(1)

        blocked = [
            "mgallery",
            "mini",
            "board"
        ]

        if gid not in blocked:
            return gid

    return None


def build_gallery_url(gallery_id):
    return (
        "https://gall.dcinside.com/"
        f"board/lists/?id={gallery_id}"
    )


def extract_gallery_name(soup):
    title = soup.select_one(".title_subject")

    if title:
        return title.text.strip()

    return "갤러리"


def parse_date(date_text):
    now = datetime.now()

    try:
        if "." in date_text and ":" not in date_text:
            month, day = map(int, date_text.split("."))

            return datetime(
                now.year,
                month,
                day
            )

        if "-" in date_text:
            return datetime.strptime(
                date_text,
                "%Y-%m-%d"
            )

    except:
        return None

    return None


def crawl_gallery(user_url, days=7):
    gallery_id = extract_gallery_id(user_url)

    if not gallery_id:
        raise Exception("갤러리 ID 추출 실패")

    base_url = build_gallery_url(gallery_id)

    print("FINAL BASE URL:", base_url)

    limit_date = (
        datetime.now() - timedelta(days=days)
    )

    nick_counter = Counter()

    gallery_name = ""
    total_posts = 0

    page = 1

    while True:
        params = {
            "id": gallery_id,
            "page": page
        }

        print("PAGE:", page)

        res = requests.get(
            "https://gall.dcinside.com/board/lists/",
            params=params,
            headers=HEADERS,
            timeout=10
        )

        print("REQUEST URL:", res.url)
        print("STATUS:", res.status_code)

        if res.status_code != 200:
            raise Exception(
                f"HTTP {res.status_code}"
            )

        soup = BeautifulSoup(
            res.text,
            "html.parser"
        )

        if not gallery_name:
            gallery_name = extract_gallery_name(
                soup
            )

        rows = soup.select("tr.ub-content")

        if not rows:
            break

        stop = False

        for row in rows:
            if "notice" in row.get("class", []):
                continue

            date_el = row.select_one(".gall_date")

            if not date_el:
                continue

            date_text = (
                date_el.get("title")
                or date_el.text.strip()
            )

            date_text = date_text[:10]

            post_date = parse_date(date_text)

            if not post_date:
                continue

            if post_date < limit_date:
                stop = True
                break

            writer = row.select_one(".gall_writer")

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

            nick_counter[nickname] += 1
            total_posts += 1

        if stop:
            break

        page += 1

    result = []

    rank = 1

    for nick, count in nick_counter.most_common():
        share = round(
            (count / total_posts) * 100,
            2
        )

        result.append({
            "rank": rank,
            "nickname": nick,
            "count": count,
            "share": share
        })

        rank += 1

    return {
        "gallery": gallery_name,
        "total": total_posts,
        "result": result
    }