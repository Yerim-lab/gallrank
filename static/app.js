let last = null;

async function runCrawl() {
    const url = document.getElementById("urlInput").value.trim();
    if (!url) return;

    setLoading(true);

    try {
        const res = await fetch("/api/crawl", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ url })
        });

        const text = await res.text();
        console.log("STATUS:", res.status);
        console.log("RAW:", text);

        const data = JSON.parse(text);

        last = data;

        if (data.error) {
            alert(data.error);
            setLoading(false);
            return;
        }

        render(data);

    } catch (e) {
        console.error(e);
    }

    setLoading(false);
}


function setLoading(state) {
    const icon = document.querySelector(".icon");
    const dots = document.querySelector(".dots");

    icon.style.display = state ? "none" : "block";
    dots.style.display = state ? "flex" : "none";
}


function render(data) {
    const box = document.getElementById("result");
    const tbody = document.getElementById("tbody");

    tbody.innerHTML = "";

    if (!data.data.length) {
        alert("결과 없음");
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


function copy() {
    if (!last) return;

    let t = "순위\t닉네임\t글수\t지분\n";

    last.data.forEach(r => {
        t += `${r.rank}\t${r.nickname}\t${r.count}\t${r.share}%\n`;
    });

    navigator.clipboard.writeText(t);
}