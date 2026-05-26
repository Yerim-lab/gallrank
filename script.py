import requests
import time

from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta


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


def fetch(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        if response.status_code == 200:
            return response.text

        return None

    except:
        return None


def parse_datetime(text):

    text = text.strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y.%m.%d %H:%M:%S"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(text, fmt)
        except:
            pass

    return None


def get_cutoff_datetime():

    now = datetime.now()

    seven_days_ago = now - timedelta(days=7)

    cutoff = datetime(
        year=seven_days_ago.year,
        month=seven_days_ago.month,
        day=seven_days_ago.day,
        hour=0,
        minute=0,
        second=0
    )

    return cutoff


def crawl(base_url):

    cutoff = get_cutoff_datetime()

    counter = defaultdict(int)

    page = 1

    while True:

        separator = "&" if "?" in base_url else "?"

        url = f"{base_url}{separator}page={page}"

        html = fetch(url)

        if not html:
            break

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        rows = soup.select("tr.ub-content")

        if not rows:
            break

        found_recent_post = False

        for row in rows:

            writer = row.select_one(".gall_writer")
            date = row.select_one(".gall_date")

            if not writer or not date:
                continue

            nick = (
                writer.get("data-nick")
                or writer.text.strip()
            )

            nick = nick.strip()

            if not nick:
                continue

            # 관리자 제외
            if nick in ["운영자", "관리자"]:
                continue

            date_text = (
                date.get("title")
                or date.text.strip()
            )

            post_time = parse_datetime(date_text)

            if not post_time:
                continue

            # 최근 7일 범위 집계
            if post_time >= cutoff:

                counter[nick] += 1

                found_recent_post = True

        # 현재 페이지에 최근 글이 하나도 없으면 종료
        if not found_recent_post:
            break

        page += 1

        # 서버 과부하 방지
        time.sleep(0.2)

    ranking = sorted(
        counter.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return ranking[:50]