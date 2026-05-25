const btn = document.getElementById("searchBtn");
const input = document.getElementById("urlInput");
const result = document.getElementById("result");

const icon = btn.querySelector(".icon");
const dots = document.getElementById("loadingDots");

btn.addEventListener("click", async () => {
    const url = input.value.trim();
    if (!url) return;

    btn.disabled = true;

    // 상태 전환: 아이콘 숨기고 점 표시
    icon.style.display = "none";
    dots.classList.remove("hidden");

    result.innerHTML = "";

    try {
        const res = await fetch("/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.error || "error");

        result.innerHTML = `
            <h3>${data.title}</h3>
            <ul>
                ${data.items.map(i => `<li>${i}</li>`).join("")}
            </ul>
        `;

    } catch (err) {
        result.innerHTML = `<p>${err.message}</p>`;
    } finally {
        btn.disabled = false;

        icon.style.display = "block";
        dots.classList.add("hidden");
    }
});