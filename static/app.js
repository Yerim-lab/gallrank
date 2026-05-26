const input = document.getElementById("urlInput");
const searchBtn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");
const result = document.getElementById("result");

let latest = null;

function escapeHtml(str) {
    return document.createElement("div").appendChild(
        document.createTextNode(str)
    ).parentNode.innerHTML;
}

async function search() {

    const url = input.value.trim();
    if (!url) return;

    result.innerHTML = "로딩중...";

    const res = await fetch(`/api/rank?url=${encodeURIComponent(url)}`);
    const data = await res.json();

    latest = data;

    render(data);
}

function render(data) {

    let html = `
        <div class="result-box">

        <button class="copy-btn" onclick="copyData()">
            <svg viewBox="0 0 24 24" width="18" height="18">
                <rect x="9" y="9" width="13" height="13" fill="none" stroke="white" stroke-width="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                      fill="none" stroke="white" stroke-width="2"/>
            </svg>
        </button>

        <table>
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

    for (const r of data.result) {
        html += `
            <tr>
                <td>${r.rank}</td>
                <td>${escapeHtml(r.nickname)}</td>
                <td>${r.count}</td>
                <td>${r.share}%</td>
            </tr>
        `;
    }

    html += `</tbody></table></div>`;

    result.innerHTML = html;
}

async function copyData() {

    if (!latest) return;

    let text = "";

    text += `${latest.gallery}\n`;
    text += `순위\t닉네임\t글수\t지분\n`;

    for (const r of latest.result) {
        text += `${r.rank}\t${r.nickname}\t${r.count}\t${r.share}%\n`;
    }

    await navigator.clipboard.writeText(text);
}

searchBtn.onclick = search;

pasteBtn.onclick = async () => {
    input.value = await navigator.clipboard.readText();
};

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") search();
});