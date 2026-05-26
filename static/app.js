async function runCrawl() {
    const url = document.getElementById("urlInput").value;

    const res = await fetch("/api/crawl", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ url })
    });

    const data = await res.json();

    const tbody = document.getElementById("resultBody");
    tbody.innerHTML = "";

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.rank}</td>
            <td>${row.nickname}</td>
            <td>${row.id}</td>
            <td>${row.count}</td>
            <td>${row.share}%</td>
        `;

        tbody.appendChild(tr);
    });
}