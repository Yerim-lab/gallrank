from flask import Flask, render_template, request, jsonify
from script import crawl, extract_gallery_name

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "no url"}), 400

    rank = crawl(url)

    total = sum(c for _, c in rank)

    return jsonify({
        "gallery": extract_gallery_name(url),
        "rank": [
            {
                "nick": n,
                "count": c,
                "ratio": round((c / total) * 100, 4) if total else 0
            }
            for n, c in rank
        ]
    })


if __name__ == "__main__":
    app.run(debug=True)