const input = document.getElementById("urlInput");
const button = document.getElementById("searchBtn");
const result = document.getElementById("result");

let loading = false;


/* =========================
   로딩 애니메이션
========================= */

function setLoading(state) {
    loading = state;

    if (state) {
        button.disabled = true;

        button.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    } else {
        button.disabled = false;

        button.innerHTML = `
            <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <circle cx="11" cy="11" r="7"></circle>
                <line x1="16.65" y1="16.65" x2="21" y2="21"></line>
            </svg>
        `;
    }
}


/* =========================
   숫자 포맷
========================= */

function numberFormat(num) {
    return num.toLocaleString();
}


/* =========================
   테이블 생성
========================= */

function createTable(data) {
    let html = `
        <div class="gallery-header">
            <h2>${data.gallery}</h2>

            <div class="gallery-total">
                총 게시글 ${numberFormat(data.total)}개
            </div>
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
    `;

    data.result.forEach(row => {
        html += `
            <tr>
                <td>${row.rank}</td>

                <td class="nickname">
                    ${escapeHtml(row.nickname)}
                </td>

                <td>
                    ${numberFormat(row.count)}
                </td>

                <td>
                    ${row.share}%
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    return html;
}


/* =========================
   HTML Escape
========================= */

function escapeHtml(text) {
    const div = document.createElement("div");

    div.innerText = text;

    return div.innerHTML;
}


/* =========================
   에러 출력
========================= */

function showError(message) {
    result.innerHTML = `
        <div class="error-box">
            ${escapeHtml(message)}
        </div>
    `;
}


/* =========================
   검색 실행
========================= */

async function searchGallery() {
    if (loading) return;

    const url = input.value.trim();

    if (!url) {
        showError("URL을 입력하세요.");
        return;
    }

    setLoading(true);

    result.innerHTML = `
        <div class="loading-text">
            집계 중...
        </div>
    `;

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error(
                "JSON 응답 파싱 실패"
            );
        }

        console.log(data);

        if (!response.ok) {
            throw new Error(
                data.error || "서버 오류"
            );
        }

        if (data.error) {
            throw new Error(data.error);
        }

        if (!data.result || !Array.isArray(data.result)) {
            throw new Error(
                "잘못된 응답 형식"
            );
        }

        result.innerHTML = createTable(data);

    } catch (error) {
        console.error(error);

        showError(
            error.message || "에러 발생"
        );

    } finally {
        setLoading(false);
    }
}


/* =========================
   버튼 클릭
========================= */

button.addEventListener(
    "click",
    searchGallery
);


/* =========================
   엔터 검색
========================= */

input.addEventListener("keydown", e => {
    if (e.key === "Enter") {
        searchGallery();
    }
});


/* =========================
   초기 아이콘 세팅
========================= */

setLoading(false);