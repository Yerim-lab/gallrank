from flask import Flask, request, jsonify, render_template
from script import crawl_gallery, normalize_dc_url
import traceback

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

    print("INPUT URL:", user_url)
    print("NORMALIZED URL:", normalized_url)

    if not normalized_url:
        return jsonify({
            "error": "올바른 디시 URL이 아닙니다."
        })

    try:
        data = crawl_gallery(normalized_url)

        return jsonify(data)

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True
    )