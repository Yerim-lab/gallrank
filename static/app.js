const input = document.getElementById("urlInput");
const searchBtn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");
const result = document.getElementById("result");

let latestData = null;
let loading = false;


function createSearchIcon() {
    return `
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
            viewBox="0 0 24 24" fill="none" stroke="white"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <line x1="16.65" y1="16.65" x2="21" y2="21"/>
        </svg>
    `;
}

function createCopyIcon() {
    return `
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
            viewBox="0 0 24 24" fill="none" stroke="white"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
    `;
}

function createCheckIcon() {
    return `
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
            viewBox="0 0 24 24" fill="none" stroke="white"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
    `;
}


function setLoading(state) {
    loading = state;

    if (state) {
        searchBtn.innerHTML = `
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        `;
    } else {
        searchBtn.innerHTML = createSearchIcon();
    }
}


function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}


/**
 * 결과 렌더링
 * - 기간 표시 제거
 * - range_text (백엔드) 사용
 */
function renderResult(data) {
    return `
        <div class="result-box">

            <div class="result-header">

                <div class="result-info">

                    <h2>${escapeHtml(data.gallery)}</h2>

                    <div class="result-date">
                        ${escapeHtml(data.range_text ?? "최근 100 페이지 집계")}
                    </div>

                </div>

                <button class="copy-btn" onclick="copyResult()">
                    ${createCopyIcon()}
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
                            <td>${escapeHtml(row.nickname)}</td>
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
    result.innerHTML = "";

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await response.json();

        if (data.error) throw new Error(data.error);

        latestData = data;
        result.innerHTML = renderResult(data);

    } catch (e) {
        console.error(e);

        result.innerHTML = `
            <div class="error-box">
                ${escapeHtml(e.message)}
            </div>
        `;
    } finally {
        setLoading(false);
    }
}


/**
 * 복사
 * - 기간 → range_text로 변경
 */
async function copyResult() {
    if (!latestData) return;

    let text = "";

    text += `${latestData.gallery}\n`;
    text += `${latestData.range_text ?? "최근 100 페이지 집계"}\n`;
    text += `순위\t닉네임\t글수\t지분\n`;

    latestData.result.forEach(row => {
        text += `${row.rank}\t${row.nickname}\t${row.count}\t${row.share}%\n`;
    });

    await navigator.clipboard.writeText(text);

    const btn = document.querySelector(".copy-btn");
    if (!btn) return;

    btn.classList.add("copied");
    btn.innerHTML = createCheckIcon();

    setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = createCopyIcon();
    }, 1200);
}


searchBtn.addEventListener("click", searchGallery);

input.addEventListener("keydown", e => {
    if (e.key === "Enter") searchGallery();
});

pasteBtn.addEventListener("click", async () => {
    try {
        const text = await navigator.clipboard.readText();
        input.value = text;
    } catch (e) {
        console.error(e);
    }
});

window.copyResult = copyResult;

setLoading(false);