const input = document.getElementById("urlInput");
const searchBtn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");
const result = document.getElementById("result");

let latestData = null;
let loading = false;

/* ---------------------------
   URL 정규화 (중요)
--------------------------- */
function normalizeDcUrl(url) {
    try {
        url = url.trim();

        // m.dcinside → gall.dcinside로 통일
        url = url.replace("m.dcinside.com", "gall.dcinside.com");

        // query 없이 board id만 있는 경우 보정
        if (!url.includes("http")) {
            url = "https://gall.dcinside.com/board/lists/?id=" + url;
        }

        return url;
    } catch (e) {
        return url;
    }
}

/* ---------------------------
   안전 텍스트 처리
--------------------------- */
function safeText(v) {
    if (!v) return "-";
    if (typeof v !== "string") return String(v);
    if (v === "undefined") return "-";
    if (v === "null") return "-";
    return v;
}

/* ---------------------------
   갤러리 이름 우선순위 정리
   (여기가 핵심 버그 해결)
--------------------------- */
function getGalleryName(data) {
    return (
        data.galleryName ||
        data.gallery_title ||
        data.title ||
        data.gallery ||
        "알 수 없는 갤러리"
    );
}

/* ---------------------------
   로딩
--------------------------- */
function setLoading(state) {
    loading = state;
    searchBtn.disabled = state;
    searchBtn.textContent = state ? "..." : "🔍";
}

/* ---------------------------
   렌더링
--------------------------- */
function render(data) {

    const gallery = safeText(getGalleryName(data));

    const rows = (data.result || []).map(r => `
        <tr>
            <td>${r.rank ?? "-"}</td>
            <td>${safeText(r.nickname)}</td>
            <td>${r.count ?? 0}</td>
            <td>${r.share ?? 0}%</td>
        </tr>
    `).join("");

    return `
        <div class="result-box">

            <div class="result-header">
                <div>
                    <h2>${gallery}</h2>
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
                    ${rows}
                </tbody>
            </table>

        </div>
    `;
}

/* ---------------------------
   검색
--------------------------- */
async function search() {

    if (loading) return;

    const url = normalizeDcUrl(input.value);
    if (!url) return;

    setLoading(true);
    result.innerHTML = "";

    try {
        const res = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || "서버 오류");
        }

        latestData = data;
        result.innerHTML = render(data);

    } catch (err) {

        result.innerHTML = `
            <div class="error-box">
                ${safeText(err.message)}
            </div>
        `;

    } finally {
        setLoading(false);
    }
}

/* ---------------------------
   paste
--------------------------- */
pasteBtn.onclick = async () => {
    const text = await navigator.clipboard.readText();
    input.value = text;
};

/* ---------------------------
   events
--------------------------- */
searchBtn.onclick = search;

input.addEventListener("keydown", e => {
    if (e.key === "Enter") search();
});