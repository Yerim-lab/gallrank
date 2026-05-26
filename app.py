from flask import Flask, request, jsonify, render_template
from script import crawl_gallery, normalize_dc_url

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/rank")
def api_rank():
    user_url = request.args.get("url", "").strip()

    if not user_url:
        return jsonify({
            "error": "URL을 입력하세요."
        })

    normalized_url = normalize_dc_url(user_url)

    if not normalized_url:
        return jsonify({
            "error": "잘못된 URL"
        })

    try:
        data = crawl_gallery(normalized_url)
        return jsonify(data)

    except Exception as e:
        print(e)

        return jsonify({
            "error": "크롤링 실패"
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)