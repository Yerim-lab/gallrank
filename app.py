from flask import Flask, request, jsonify, send_from_directory
from script import crawl_gallery, normalize_dc_url

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


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
            "error": "올바른 디시 URL이 아닙니다."
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
    app.run(debug=True)