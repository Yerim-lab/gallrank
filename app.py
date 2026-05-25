from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    url = request.json.get("url")

    # 예시 데이터 (여기 네 크롤링 결과 들어가면 됨)
    result = [
        {"rank": 1, "nick": "A", "posts": 120, "share": "32.1%"},
        {"rank": 2, "nick": "B", "posts": 98, "share": "25.4%"},
    ]

    return jsonify({
        "gallery": "갤러리 이름",
        "range": "2026.01.01 ~ 2026.01.25",
        "result": result
    })


if __name__ == "__main__":
    app.run(debug=True)