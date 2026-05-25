if __name__ == "__main__":

ts
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://gall.dcinside.com/"
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

        found = False

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
                found = True

        if not found:
            break

        page += 1
        time.sleep(0.2)

    return sorted(count.items(), key=lambda x: x[1], reverse=True)[:50]