const btn = document.getElementById("searchBtn");
const pasteBtn = document.getElementById("pasteBtn");
const input = document.getElementById("urlInput");

const board = document.getElementById("board");
const result = document.getElementById("result");

const titleEl = document.getElementById("galleryTitle");
const dateEl = document.getElementById("dateRange");

const copyBtn = document.getElementById("copyBtn");

/* =========================
   LOADING STATE
========================= */
function setLoading(state) {
    btn.classList.toggle("loading", state);
    btn.disabled = state;
    input.disabled = state;
    pasteBtn.disabled = state;
}

/* =========================
   PASTE
========================= */
pasteBtn.addEventListener("click", async () => {
    try {
        const text = await navigator.clipboard.readText();
        if (text) input.value = text;
    } catch {
        alert("붙여넣기 실패");
    }
});

/* =========================
   DATE RANGE (7 days)
========================= */
function formatDateRange() {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 7);

    const fmt = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}년 ${m}월 ${day}일`;
    };

    return `${fmt(start)}부터 ${fmt(end)}까지`;
}

/* =========================
   RATIO FORMAT (x.xx%)
========================= */
function formatRatio(v) {
    const num = Number(v);
    if (isNaN(num)) return "0.00%";
    return num.toFixed(2) + "%";
}

/* =========================
   RENDER RESULT
========================= */
function render(data) {

    const list = (data.rank || []).slice(0, 50);

    result.innerHTML = list.map((item, i) => `
        <div class="row">
            <div class="rank">${i + 1}</div>
            <div class="nick">${item.nick ?? ""}</div>
            <div class="count">${item.count ?? 0}</div>
            <div class="ratio">${formatRatio(item.ratio)}</div>
        </div>
    `).join("");

    titleEl.textContent = data.gallery || "갤러리";
    dateEl.textContent = formatDateRange();

    board.classList.add("show");
}

/* =========================
   SEARCH
========================= */
btn.addEventListener("click", async () => {

    const url = input.value.trim();
    if (!url || btn.classList.contains("loading")) return;

    setLoading(true);

    board.classList.remove("show");
    result.innerHTML = "";

    try {
        const res = await fetch("/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        if (!res.ok) throw new Error("request failed");

        const data = await res.json();

        render(data);

    } catch (e) {
        alert("에러 발생");
    }

    setLoading(false);
});

/* =========================
   COPY
========================= */
copyBtn.addEventListener("click", async () => {

    const gallery = titleEl?.innerText || "";
    const date = dateEl?.innerText || "";

    const rows = document.querySelectorAll(".row");

    let text = "";

    // header
    text += `${gallery}\n`;
    text += `${date}\n\n`;

    // body
    rows.forEach(r => {
        const cols = r.querySelectorAll("div");

        const rank = cols[0]?.innerText || "";
        const nick = cols[1]?.innerText || "";
        const count = cols[2]?.innerText || "";
        const ratio = cols[3]?.innerText || "";

        text += `${rank}\t${nick}\t${count}\t${ratio}\n`;
    });

    try {
        await navigator.clipboard.writeText(text);

        copyBtn.innerText = "복사됨";
        setTimeout(() => copyBtn.innerText = "복사", 1000);

    } catch {
        alert("복사 실패");
    }
});