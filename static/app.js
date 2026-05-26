const input = document.getElementById("urlInput");
const pasteBtn = document.getElementById("pasteBtn");
const searchBtn = document.getElementById("searchBtn");
const result = document.getElementById("result");

let latest = null;
let loading = false;

async function search() {

    if (loading) return;

    const url = input.value.trim();
    if (!url) return;

    loading = true;
    result.innerHTML = "";

    try {

        const res = await fetch(`/api/rank?url=${encodeURIComponent(url)}`);
        const text = await res.text();

        let data;
        try {
            data = JSON.parse(text);
        } catch {
            throw new Error("서버 응답이 JSON이 아님");
        }

        if (data.error) throw new Error(data.error);

        latest = data;
        render(data);

    } catch (e) {
        result.innerHTML = `<div class="result-box">${e.message}</div>`;
    }

    loading = false;
}

function render(data) {

    let html = `
        <div class="result-box">

            <button class="copy-btn" onclick="copyData()">
                <svg viewBox="0 0 24 24">
                    <rect x="9" y="9" width="10" height="10" rx="2"/>
                    <path d="M5 15V5h10"/>
                </svg>
            </button>

            <div style="font-weight:700;font-size:18px;">
                ${escape(data.gallery)}
            </div>

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
                <td>${escape(r.nickname)}</td>
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

    let text =
        `${latest.gallery}\n` +
        `순위\t닉네임\t글수\t지분\n`;

    for (const r of latest.result) {
        text += `${r.rank}\t${r.nickname}\t${r.count}\t${r.share}%\n`;
    }

    await navigator.clipboard.writeText(text);
}

pasteBtn.onclick = async () => {
    try {
        input.value = await navigator.clipboard.readText();
    } catch {}
};

searchBtn.onclick = search;

function escape(str) {
    return (str || "").replace(/[&<>"']/g, m => ({
        "&":"&amp;",
        "<":"&lt;",
        ">":"&gt;",
        "\"":"&quot;",
        "'":"&#039;"
    }[m]));
}