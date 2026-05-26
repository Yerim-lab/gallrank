from flask import Flask, render_template, request, jsonify

from script import crawl, fetch

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


def get_gallery_name(url):

    html = fetch(url)

    if not html:
        return "갤러리"

    soup = BeautifulSoup(html, "html.parser")

    meta = soup.select_one('meta[name="description"]')

    if not meta:
        return "갤러리"

    content = meta.get("content", "")

    # "레드벨벳의레벨업 마이너 갤러리 - ..."
    name = content.split("-")[0].strip()

    return name


@app.route("/search", methods=["POST"])
def search():

    try:

        url = request.json.get("url", "").strip()

        if not url:
            return jsonify({
                "gallery": "-",
                "range": "-",
                "result": []
            })

        ranking = crawl(url)

        total_posts = sum(posts for _, posts in ranking)

        result = []

        for idx, (nick, posts) in enumerate(ranking, start=1):

            share = 0

            if total_posts > 0:
                share = round(
                    (posts / total_posts) * 100,
                    2
                )

            result.append({
                "rank": idx,
                "nick": nick,
                "posts": posts,
                "share": f"{share}%"
            })

        gallery_name = get_gallery_name(url)

        today = datetime.now()
        start = today - timedelta(days=7)

        range_text = (
            f"{start.year}년 "
            f"{start.month:02d}월 "
            f"{start.day:02d}일"
            " - "
            f"{today.year}년 "
            f"{today.month:02d}월 "
            f"{today.day:02d}일"
        )

        return jsonify({
            "gallery": gallery_name,
            "range": range_text,
            "result": result
        })

    except Exception as e:

        print(e)

        return jsonify({
            "gallery": "ERROR",
            "range": "-",
            "result": []
        })


if __name__ == "__main__":
    app.run(debug=True)