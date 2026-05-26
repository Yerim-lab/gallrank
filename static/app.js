const input = document.getElementById("urlInput");
const searchBtn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");
const result = document.getElementById("result");
const status = document.getElementById("status");

let loading = false;

function setStatus(msg) {
    status.textContent = msg || "";
}

function isValidJson(text) {
    try {
        JSON.parse(text);
        return true;
    } catch {
        return false;
    }
}

async function search() {

    if (loading) return;

    const url = input.value.trim();
    if (!url) return;

    loading = true;
    setStatus("분석 중...");

    result.innerHTML = "";

    try {

        const res = await fetch(`/api/rank?url=${encodeURIComponent(url)}`);

        const text = await res.text();

        if (!isValidJson(text)) {
            throw new Error("서버 응답이 JSON이 아님 (HTML 반환됨)");
        }

        const data = JSON.parse(text);

        if (data.error) {
            throw new Error(data.error);
        }

        render(data);
        setStatus("");

    } catch (e) {

        console.error(e);
        setStatus(e.message);

        result.innerHTML =
            `<div class="error">${e.message}</div>`;
    }

    loading = false;
}

function render(data) {

    let html = `
        <div class="result-box">
            <div class="result-header">
                <h2>${data.gallery}</h2>
            </div>

            <table class="result-table">
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>닉네임</th>
                        <th>글수</th>
                        <th>지분</th>
                    </tr>
                </thead>
                <tbody>
    `;

    for (const row of data.result) {
        html += `
            <tr>
                <td>${row.rank}</td>
                <td>${escapeHtml(row.nickname)}</td>
                <td>${row.count}</td>
                <td>${row.share}%</td>
            </tr>
        `;
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    result.innerHTML = html;
}

function escapeHtml(str) {
    return str.replace(/[&<>"']/g, m => ({
        "&":"&amp;",
        "<":"&lt;",
        ">":"&gt;",
        "\"":"&quot;",
        "'":"&#039;"
    }[m]));
}

searchBtn.onclick = search;

input.addEventListener("keydown", e => {
    if (e.key === "Enter") search();
});

pasteBtn.onclick = async () => {
    try {
        input.value = await navigator.clipboard.readText();
    } catch {}
};