const input = document.getElementById("urlInput");
    if (!url) return;

    setLoading(true);

    try {
        const response = await fetch(
            `/api/rank?url=${encodeURIComponent(url)}`
        );

        const data = await response.json();

        console.log(data);

        if (data.error) {
            throw new Error(data.error);
        }

        latestData = data;

        result.innerHTML = renderResult(data);

    } catch (e) {
        console.error(e);

        result.innerHTML = `
            <div class="error-box">
                ${escapeHtml(e.message)}
            </div>
        `;

    } finally {
        setLoading(false);
    }
}


searchBtn.addEventListener(
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


pasteBtn.addEventListener(
    "click",
    async () => {
        try {
            const text = await navigator.clipboard.readText();

            input.value = text;

        } catch (e) {
            console.error(e);
        }
    }
);


window.copyResult = copyResult;

setLoading(false);