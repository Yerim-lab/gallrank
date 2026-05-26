const input =
    document.getElementById("urlInput");

const searchBtn =
    document.getElementById("searchBtn");

const pasteBtn =
    document.getElementById("pasteBtn");

const result =
    document.getElementById("result");

let latestData = null;


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


function render(data) {
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


async function search() {
    const url = input.value.trim();

    if (!url) return;

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        latestData = data;

        result.innerHTML = render(data);

    } catch (e) {
        result.innerHTML = `
            <div class="error-box">
                ${e.message}
            </div>
        `;
    }
}


async function copyResult() {
    if (!latestData) return;

    let text = "";

    text += `${latestData.gallery}\n`;

    text += `${getDate(-7)}\t${getDate()}\n`;

    text += `순위\t닉네임\t글수\t지분\n`;

    latestData.result.forEach(row => {
        text += (
            `${row.rank}\t` +
            `${row.nickname}\t` +
            `${row.count}\t` +
            `${row.share}%\n`
        );
    });

    await navigator.clipboard.writeText(
        text
    );
}


searchBtn.addEventListener(
    "click",
    search
);

input.addEventListener(
    "keydown",
    e => {
        if (e.key === "Enter") {
            search();
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