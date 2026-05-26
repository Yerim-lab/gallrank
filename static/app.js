const btn = document.getElementById("searchBtn");

const pasteBtn = document.getElementById("pasteBtn");

const input = document.getElementById("urlInput");

const resultBox = document.getElementById("result");


btn.addEventListener("click", async () => {

    const url = input.value.trim();

    if (!url || btn.classList.contains("loading")) {
        return;
    }

    setLoading(true);

    try {

        const response = await fetch("/search", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                url
            })

        });

        if (!response.ok) {
            throw new Error("서버 오류");
        }

        const data = await response.json();

        renderResult(data);

    } catch (err) {

        console.error(err);

        resultBox.innerHTML = `
            <div class="result-card error">
                에러 발생
            </div>
        `;

    } finally {

        setLoading(false);

    }

});


pasteBtn.addEventListener("click", async () => {

    try {

        const text = await navigator.clipboard.readText();

        input.value = text;

    } catch (err) {

        console.error(err);

        alert("붙여넣기 실패");

    }

});


function setLoading(isLoading) {

    if (isLoading) {
        btn.classList.add("loading");
    } else {
        btn.classList.remove("loading");
    }

}


function renderResult(data) {

    const list = Array.isArray(data.result)
        ? data.result
        : [];

    resultBox.innerHTML = `
        <div class="result-card">

            <div class="result-header">

                <div class="header-left">

                    <div class="gallery-name">
                        ${data.gallery || "-"}
                    </div>

                    <div class="date-range">
                        ${data.range || "-"}
                    </div>

                </div>

                <button
                    class="copy-btn"
                    onclick="copyResult()"
                    type="button"
                >
                    복사
                </button>

            </div>

            <div class="table-box">

                <div class="table-row table-head">
                    <span>순위</span>
                    <span>닉네임</span>
                    <span>글수</span>
                    <span>지분</span>
                </div>

                ${list.map(item => `
                    <div class="table-row">
                        <span>${item.rank ?? "-"}</span>
                        <span>${item.nick ?? "-"}</span>
                        <span>${item.posts ?? "-"}</span>
                        <span>${item.share ?? "-"}</span>
                    </div>
                `).join("")}

            </div>

        </div>
    `;
}


async function copyResult() {

    try {

        const gallery =
            document.querySelector(".gallery-name")
            ?.innerText
            ?.trim() || "";

        const range =
            document.querySelector(".date-range")
            ?.innerText
            ?.trim() || "";

        const rows = document.querySelectorAll(
            ".table-row"
        );

        let text = "";

        text += `${gallery}\n`;
        text += `${range}\n`;

        rows.forEach(row => {

            const cols = row.querySelectorAll("span");

            const line = Array.from(cols)
                .map(col => col.innerText.trim())
                .join("\t");

            text += `${line}\n`;

        });

        await navigator.clipboard.writeText(text);

    } catch (err) {

        console.error(err);

        alert("복사 실패");

    }

}