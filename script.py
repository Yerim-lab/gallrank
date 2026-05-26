from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime, timedelta, time
import re

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def parse_dcinside(url):
    # 1) 기간 설정: 최근 7일 00:00 ~ 현재
    now = datetime.now()
    start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    user_count = defaultdict(int)

    page = 1

    while True:
        target_url = f"{url}?page={page}"
        res = requests.get(target_url, headers=HEADERS)
        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.text, "html.parser")

        rows = soup.select("tr.ub-content")  # DCInside 게시글 row (변경 가능)
        if not rows:
            break

        stop = False

        for row in rows:
            try:
                date_text = row.select_one(".gall_date")
                nick = row.select_one(".ub-word .nickname") or row.select_one(".nickname")
                user_id = row.select_one(".ip")

                if not date_text or not nick:
                    continue

                date_str = date_text.get_text(strip=True)

                # DCInside 날짜 포맷 대응 (예: 2026.05.26 / 05.26 / HH:MM)
                try:
                    if "." in date_str:
                        post_date = datetime.strptime(date_str, "%Y.%m.%d")
                    elif ":" in date_str:
                        post_date = now
                    else:
                        continue
                except:
                    continue

                if post_date < start_date:
                    stop = True
                    break

                nickname = nick.get_text(strip=True)
                uid = user_id.get_text(strip=True) if user_id else nickname

                user_count[(nickname, uid)] += 1

            except:
                continue

        if stop:
            break

        page += 1

    total = sum(user_count.values())

    ranked = []
    for (nick, uid), cnt in user_count.items():
        share = (cnt / total * 100) if total > 0 else 0
        ranked.append({
            "nickname": nick,
            "id": uid,
            "count": cnt,
            "share": round(share, 2)
        })

    ranked.sort(key=lambda x: x["count"], reverse=True)

    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    return ranked


@app.route("/api/crawl", methods=["POST"])
def crawl():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    result = parse_dcinside(url)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)