const input = document.getElementById("urlInput");
const searchBtn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");

const result = document.getElementById("result");
const noticeBox = document.getElementById("noticeBox");

let latestData = null;
let loading = false;


/* =========================
   안내창 표시/숨김
========================= */

function showNotice() {

    if (!noticeBox) return;

    noticeBox.style.display = "block";
}


function hideNotice() {

    if (!noticeBox) return;

    noticeBox.style.display = "none";
}


/* =========================
   아이콘
========================= */

function createSearchIcon() {

    return `
        <svg xmlns="http://www.w3.org/2000/svg"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round">

            <circle cx="11" cy="11" r="7"/>
            <line x1="16.65" y1="16.65" x2="21" y2="21"/>

        </svg>
    `;
}


function createCopyIcon() {

    return `
        <svg xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round">

            <rect x="9" y="9" width="13" height="13" rx="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>

        </svg>
    `;
}


function createCheckIcon() {

    return `
        <svg xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="white"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round">

            <polyline points="20 6 9 17 4 12"/>

        </svg>
    `;
}


/* =========================
   로딩
========================= */

function setLoading(state) {

    loading = state;

    searchBtn.disabled = state;

    if (state) {

        searchBtn.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

    } else {

        searchBtn.innerHTML = createSearchIcon();

    }
}


/* =========================
   HTML Escape
========================= */

function escapeHtml(text) {

    const div = document.createElement("div");

    div.innerText = text ?? "";

    return div.innerHTML;
}


/* =========================
   집계 문구 생성
========================= */

function getRangeText(data) {

    if (data.range_text) {
        return data.range_text;
    }

    if (typeof data.pages === "number") {
        return `최근 ${data.pages}페이지 집계`;
    }

    return "최근 페이지 집계";
}


/* =========================
   결과 렌더링
========================= */

function renderResult(data) {

    const rows = (data.result || []).map(row => {

        return `
            <tr>
                <td>${row.rank}</td>
                <td>${escapeHtml(row.nickname)}</td>
                <td>${row.count}</td>
                <td>${row.share}%</td>
            </tr>
        `;

    }).join("");

    return `
        <div class="result-box">

            <div class="result-header">

                <div class="result-info">

                    <h2>${escapeHtml(data.gallery)}</h2>

                    <div class="result-date">
                        ${escapeHtml(getRangeText(data))}
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
                    ${rows}
                </tbody>

            </table>

        </div>
    `;
}


/* =========================
   에러 렌더링
========================= */

function renderError(message) {

    return `
        <div class="error-box">
            ${escapeHtml(message)}
        </div>
    `;
}


/* =========================
   검색
========================= */

async function searchGallery() {

    if (loading) return;

    const url = input.value.trim();

    if (!url) return;

    setLoading(true);

    result.innerHTML = "";

    showNotice();

    try {

        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const rawText = await response.text();

        console.log("RAW RESPONSE:");
        console.log(rawText);

        let data;

        try {

            data = JSON.parse(rawText);

        } catch (jsonError) {

            console.error("JSON PARSE ERROR:", jsonError);

            throw new Error(
                "서버가 JSON이 아닌 응답을 반환했습니다."
            );

        }

        if (!response.ok) {

            throw new Error(
                data.error || `HTTP ${response.status}`
            );

        }

        if (data.error) {
            throw new Error(data.error);
        }

        latestData = data;

        result.innerHTML = renderResult(data);

        hideNotice();

    } catch (e) {

        console.error("SEARCH ERROR:", e);

        showNotice();

        result.innerHTML = renderError(
            e.message || "알 수 없는 오류가 발생했습니다."
        );

    } finally {

        setLoading(false);

    }
}


/* =========================
   복사
========================= */

async function copyResult() {

    if (!latestData) return;

    let text = "";

    text += `${latestData.gallery}\n`;
    text += `${getRangeText(latestData)}\n`;
    text += `순위\t닉네임\t글수\t지분\n`;

    latestData.result.forEach(row => {

        text += (
            `${row.rank}\t` +
            `${row.nickname}\t` +
            `${row.count}\t` +
            `${row.share}%\n`
        );

    });

    try {

        await navigator.clipboard.writeText(text);

        const btn = document.querySelector(".copy-btn");

        if (!btn) return;

        btn.classList.add("copied");

        btn.innerHTML = createCheckIcon();

        setTimeout(() => {

            btn.classList.remove("copied");

            btn.innerHTML = createCopyIcon();

        }, 1200);

    } catch (e) {

        console.error("COPY ERROR:", e);

    }
}


/* =========================
   이벤트
========================= */

searchBtn.addEventListener("click", searchGallery);

input.addEventListener("keydown", e => {

    if (e.key === "Enter") {
        searchGallery();
    }

});


pasteBtn.addEventListener("click", async () => {

    try {

        const text = await navigator.clipboard.readText();

        input.value = text;

    } catch (e) {

        console.error("PASTE ERROR:", e);

    }

});


window.copyResult = copyResult;


/* =========================
   초기화
========================= */

setLoading(false);
showNotice();