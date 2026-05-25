import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        return r.text if r.status_code == 200 else None
    except:
        return None


def crawl(base_url):
    cutoff = datetime.now() - timedelta(days=7)
    count = defaultdict(int)

    page = 1

    while True:
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}page={page}"

        html = fetch(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr.ub-content")

        if not rows:
            break

        valid = False

        for row in rows:
            writer = row.select_one(".gall_writer")
            date = row.select_one(".gall_date")

            if not writer or not date:
                continue

            nick = writer.get("data-nick") or writer.text.strip()
            dt = date.get("title") or date.text.strip()

            try:
                t = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except:
                continue

            if t >= cutoff:
                count[nick] += 1
                valid = True

        if not valid:
            break

        page += 1

    return sorted(count.items(), key=lambda x: x[1], reverse=True)[:50]


def extract_gallery_name(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        meta = soup.find("meta", {"name": "description"})
        if meta:
            return meta.get("content", "").split("-")[0].strip()

    except:
        pass

    return "갤러리"