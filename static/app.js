let lastResult = [];

async function runCrawl() {
    const url = document.getElementById("urlInput").value.trim();
    if (!url) return;

    setLoading(true);

    try {
        const res = await fetch("/api/crawl", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        const data = await res.json();
        lastResult = Array.isArray(data) ? data : [];

        render(lastResult);

    } catch (e) {
        console.error(e);
    }

    setLoading(false);
}

function setLoading(state) {
    const icon = document.querySelector(".icon-search");
    const dots = document.querySelector(".loading-dots");

    icon.style.display = state ? "none" : "block";
    dots.style.display = state ? "flex" : "none";
}

function render(data) {
    const box = document.getElementById("resultBox");
    const tbody = document.getElementById("resultBody");

    tbody.innerHTML = "";

    if (!data.length) {
        box.classList.add("hidden");
        return;
    }

    document.getElementById("metaInfo").innerText = "최근 7일 기준";

    data.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${r.rank}</td>
            <td>${r.nickname}</td>
            <td>${r.count}</td>
            <td>${r.share}%</td>
        `;
        tbody.appendChild(tr);
    });

    box.classList.remove("hidden");
}

function copyResult() {
    let text = "순위\t닉네임\t글수\t지분\n";

    lastResult.forEach(r => {
        text += `${r.rank}\t${r.nickname}\t${r.count}\t${r.share}%\n`;
    });

    navigator.clipboard.writeText(text);
}