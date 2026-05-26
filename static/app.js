const input =
    document.getElementById("urlInput");

const button =
    document.getElementById("searchBtn");

const result =
    document.getElementById("result");

let loading = false;


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
                <circle
                    cx="11"
                    cy="11"
                    r="7"
                ></circle>

                <line
                    x1="16.65"
                    y1="16.65"
                    x2="21"
                    y2="21"
                ></line>
            </svg>
        `;
    }
}


function escapeHtml(text) {
    const div =
        document.createElement("div");

    div.innerText = text;

    return div.innerHTML;
}


async function searchGallery() {
    if (loading) return;

    const url = input.value.trim();

    if (!url) {
        return;
    }

    setLoading(true);

    result.innerHTML = "";

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data =
            await response.json();

        console.log(data);

        if (data.error) {
            result.innerHTML = `
                <div class="error-box">
                    ${escapeHtml(data.error)}
                </div>
            `;

            setLoading(false);

            return;
        }

        let html = `
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
                    <td>
                        ${escapeHtml(row.nickname)}
                    </td>
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

    } catch (error) {
        console.error(error);

        result.innerHTML = `
            <div class="error-box">
                ${escapeHtml(error.message)}
            </div>
        `;
    }

    setLoading(false);
}


button.addEventListener(
    "click",
    searchGallery
);

input.addEventListener(
    "keydown",
    e => {
        if (e.key === "Enter") {
            searchGallery();
        }
    }
);