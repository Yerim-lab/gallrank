from flask import Flask, request, jsonify, render_template
from script import crawl_gallery
import traceback

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/rank")
def api_rank():
    user_url = request.args.get("url", "").strip()

    print("INPUT URL:", user_url)

    if not user_url:
        return jsonify({
            "error": "URL을 입력하세요."
        })

    try:
        data = crawl_gallery(user_url)

        return jsonify(data)

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        })


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "404 Not Found"
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "500 Internal Server Error"
    }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True
    )