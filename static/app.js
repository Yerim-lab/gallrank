let last = null;

async function runCrawl() {
    const url = document.getElementById("urlInput").value.trim();
    if (!url) return;

    setLoading(true);

    const res = await fetch("/api/crawl", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ url })
    });

    const data = await res.json();
    last = data;

    setLoading(false);
    render(data);
}

function setLoading(state) {
    const icon = document.querySelector(".icon");
    const dots = document.querySelector(".dots");

    icon.style.display = state ? "none" : "block";
    dots.style.display = state ? "flex" : "none";
}

function render(data) {
    const box = document.getElementById("resultBox");
    const tbody = document.getElementById("tbody");

    tbody.innerHTML = "";

    if (!data.data.length) {
        box.classList.add("hidden");
        return;
    }

    document.getElementById("meta").innerText =
        `${data.gallery || "갤러리"} · 최근 7일`;

    data.data.forEach(r => {
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

    last.data.forEach(r => {
        text += `${r.rank}\t${r.nickname}\t${r.count}\t${r.share}%\n`;
    });

    navigator.clipboard.writeText(text);
}