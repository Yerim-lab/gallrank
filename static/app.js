const btn = document.getElementById("searchBtn");
const input = document.getElementById("urlInput");
const resultBox = document.getElementById("result");
const dots = document.getElementById("loadingDots");

btn.addEventListener("click", async () => {
    const url = input.value.trim();
    if (!url) return;

    setLoading(true);

    try {
        const res = await fetch("/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url })
        });

        const data = await res.json();

        renderResult(data);

    } catch (err) {
        console.error(err);
        resultBox.innerHTML = "<div>에러 발생</div>";
    } finally {
        setLoading(false);
    }
});


function renderResult(data) {
    const list = Array.isArray(data.result) ? data.result : [];

    resultBox.innerHTML = `
        <div class="result-card">

            <div class="result-header">
                <div class="gallery-name">${data.gallery || "-"}</div>
                <div class="date-range">${data.range || "-"}</div>

                <button class="copy-btn" onclick="copyResult()">복사</button>
            </div>

            <div class="table-box">
                <div class="table-row table-head">
                    <span>순위</span>
                    <span>닉네임</span>
                    <span>글수</span>
                    <span>지분</span>
                </div>

                ${list.map(item => `
                    <div class="table-row">
                        <span>${item.rank ?? "-"}</span>
                        <span>${item.nick ?? "-"}</span>
                        <span>${item.posts ?? "-"}</span>
                        <span>${item.share ?? "-"}</span>
                    </div>
                `).join("")}

            </div>
        </div>
    `;
}


function setLoading(isLoading) {
    if (isLoading) {
        dots.classList.remove("hidden");
    } else {
        dots.classList.add("hidden");
    }
}


function copyResult() {
    const text = document.getElementById("result").innerText;
    navigator.clipboard.writeText(text);
}