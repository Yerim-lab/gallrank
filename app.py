from flask import Flask, render_template, request, jsonify

from script import crawl

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


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

        return jsonify({
            "gallery": "갤창랭킹",
            "range": "최근 7일 기준",
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