from flask import Flask, render_template, request, jsonify
from script import crawl  # 크롤링 로직 분리 가정
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "no url"}), 400

    try:
        result = crawl(url)

        # script.py에서 [(nick, count), ...] 형태라고 가정
        rank = []
        total = sum([c for _, c in result]) if result else 1

        for nick, count in result:
            ratio = (count / total) * 100 if total > 0 else 0
            rank.append({
                "nick": nick,
                "count": count,
                "ratio": round(ratio, 2)
            })

        return jsonify({
            "gallery": url.split("id=")[-1] if "id=" in url else "갤러리",
            "rank": rank
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)