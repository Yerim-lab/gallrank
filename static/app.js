const input = document.getElementById("urlInput");
const button = document.getElementById("searchBtn");
const result = document.getElementById("result");


button.addEventListener("click", async () => {
    const url = input.value.trim();

    if (!url) {
        result.innerHTML = "URL을 입력하세요.";
        return;
    }

    result.innerHTML = "집계 중...";

    try {
        const res = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await res.json();

        console.log(data);

        // 실제 에러 출력
        if (data.error) {
            result.innerHTML = `
                <div class="error">
                    ${data.error}
                </div>
            `;
            return;
        }

        let html = `
            <h2>${data.gallery}</h2>
            <table>
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
                    <td>${row.nickname}</td>
                    <td>${row.count}</td>
                    <td>${row.share}%</td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
        `;

        result.innerHTML = html;

    } catch (e) {
        console.error(e);

        result.innerHTML = `
            <div class="error">
                ${e.message}
            </div>
        `;
    }
});