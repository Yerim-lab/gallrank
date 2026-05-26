from flask import Flask, render_template, request, jsonify

from script import crawl

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

import requests


app = Flask(__name__)


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


@app.route("/")
def home():
    return render_template("index.html")


def get_gallery_name(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=5
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        meta = soup.select_one(
            'meta[name="description"]'
        )

        if not meta:
            return "갤러리"

        content = meta.get("content", "")

        return content.split("-")[0].strip()

    except:
        return "갤러리"


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

        total_posts = sum(
            posts for _, posts in ranking
        )

        result = []

        for idx, (nick, posts) in enumerate(
            ranking,
            start=1
        ):

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
            "gallery": get_gallery_name(url),
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