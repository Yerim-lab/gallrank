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


def normalize_dc_url(url):
    url = url.strip()

    # 이미 게시판 주소인 경우
    if "lists?id=" in url:
        return url

    # 미니 갤러리
    m = re.search(r"dcinside\.com/mini/([^/?#]+)", url)

    if m:
        gid = m.group(1)

        return (
            f"https://gall.dcinside.com/"
            f"mini/board/lists?id={gid}"
        )

    # 마이너 갤러리
    m = re.search(r"dcinside\.com/mgallery/([^/?#]+)", url)

    if m:
        gid = m.group(1)

        return (
            f"https://gall.dcinside.com/"
            f"mgallery/board/lists?id={gid}"
        )

    # 일반 갤러리
    m = re.search(r"dcinside\.com/([^/?#]+)", url)

    if m:
        gid = m.group(1)

        return (
            f"https://gall.dcinside.com/"
            f"board/lists/?id={gid}"
        )

    return None


def extract_gallery_name(soup):
    title = soup.select_one(".title_subject")

    if title:
        return title.text.strip()

    page_title = soup.title.text.strip()

    return page_title.replace(" - DC Inside", "").strip()


def parse_date(date_text):
    now = datetime.now()

    try:
        # 05.26 형태
        if "." in date_text and ":" not in date_text:
            month, day = map(int, date_text.split("."))

            return datetime(now.year, month, day)

        # 2026-05-26 형태
        if "-" in date_text:
            return datetime.strptime(
                date_text,
                "%Y-%m-%d"
            )

    except:
        return None

    return None


def crawl_gallery(url, days=7):
    limit_date = datetime.now() - timedelta(days=days)

    nick_counter = Counter()

    gallery_name = ""
    total_posts = 0

    page = 1

    while True:
        page_url = f"{url}&page={page}"

        print(f"[CRAWL] {page_url}")

        res = requests.get(
            page_url,
            headers=HEADERS,
            timeout=10
        )

        if res.status_code != 200:
            print("STATUS ERROR:", res.status_code)
            break

        soup = BeautifulSoup(
            res.text,
            "html.parser"
        )

        if not gallery_name:
            gallery_name = extract_gallery_name(soup)

        rows = soup.select("tr.ub-content")

        if not rows:
            break

        stop = False

        for row in rows:
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

            # 기간 초과
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