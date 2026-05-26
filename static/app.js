const input =
    document.getElementById("urlInput");

const searchBtn =
    document.getElementById("searchBtn");

const pasteBtn =
    document.getElementById("pasteBtn");

const result =
    document.getElementById("result");

let latestData = null;

let loading = false;


function setLoading(state) {
    loading = state;

    if (state) {
        searchBtn.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    } else {
        searchBtn.innerHTML = "🔍";
    }
}


function getDate(offset = 0) {
    const d = new Date();

    d.setDate(d.getDate() + offset);

    const y = d.getFullYear();

    const m = String(
        d.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        d.getDate()
    ).padStart(2, "0");

    return `${y}년 ${m}월 ${day}일`;
}


function createCopyText(data) {
    let text = "";

    text += `${data.gallery}\n`;

    text += `${getDate(-7)}\t${getDate()}\n`;

    text += `순위\t닉네임\t글수\t지분\n`;

    data.result.forEach(row => {
        text += (
            `${row.rank}\t` +
            `${row.nickname}\t` +
            `${row.count}\t` +
            `${row.share}%\n`
        );
    });

    return text;
}


async function copyResult() {
    if (!latestData) return;

    await navigator.clipboard.writeText(
        createCopyText(latestData)
    );
}


function renderResult(data) {
    return `
        <div class="result-box">

            <div class="result-header">

                <div>
                    <h2>${data.gallery}</h2>

                    <div>
                        ${getDate(-7)}
                        ~
                        ${getDate()}
                    </div>
                </div>

                <button
                    class="copy-btn"
                    onclick="copyResult()"
                >
                    ⧉
                </button>

            </div>

            <table class="rank-table">

                <thead>
                    <tr>
                        <th>순위</th>
                        <th>닉네임</th>
                        <th>글수</th>
                        <th>지분</th>
                    </tr>
                </thead>

                <tbody>

                    ${data.result.map(row => `
                        <tr>
                            <td>${row.rank}</td>
                            <td>${row.nickname}</td>
                            <td>${row.count}</td>
                            <td>${row.share}%</td>
                        </tr>
                    `).join("")}

                </tbody>

            </table>

        </div>
    `;
}


async function searchGallery() {
    if (loading) return;

    const url = input.value.trim();

    if (!url) return;

    setLoading(true);

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        latestData = data;

        result.innerHTML =
            renderResult(data);

    } catch (e) {
        result.innerHTML = `
            <div class="error-box">
                ${e.message}
            </div>
        `;
    }

    setLoading(false);
}


searchBtn.addEventListener(
    "click",
    searchGallery
);

input.addEventListener(
    "keydown",
    e => {
        if (e.key === "Enter") {
            searchGallery();
        }
    }
);

pasteBtn.addEventListener(
    "click",
    async () => {
        const text =
            await navigator.clipboard.readText();

        input.value = text;
    }
);

window.copyResult = copyResult;

setLoading(false);