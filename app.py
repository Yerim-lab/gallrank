from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request

from script import crawl_gallery

import traceback


app = Flask(
    __name__,
    static_folder="./static",
    template_folder="./templates"
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/rank")
def rank():
    url = request.args.get("url", "").strip()

    if not url:
        return jsonify({
            "error": "URL을 입력하세요."
        })

    try:
        data = crawl_gallery(url)

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