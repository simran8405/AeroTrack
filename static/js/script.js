// ============ REGISTRY FILTER TABS ============
document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".filter-tabs .tab");
    const rows = document.querySelectorAll(".registry-table tbody tr[data-status]");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            const filter = tab.dataset.filter;

            rows.forEach((row) => {
                if (filter === "all" || row.dataset.status === filter) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    });
});

// ============ BARCODE (deterministic pseudo-barcode from tag id) ============
function drawBarcode(canvas, seed) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#000";

    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
    }

    const rand = () => {
        hash = (hash * 1103515245 + 12345) >>> 0;
        return (hash % 1000) / 1000;
    };

    let x = 0;
    while (x < w) {
        const barWidth = 1 + Math.floor(rand() * 4);
        if (rand() > 0.45) {
            ctx.fillRect(x, 0, barWidth, h);
        }
        x += barWidth + 1;
    }
}

// ============ OPERATIONS CHARTS ============
function initOperationsCharts(throughputData, distributionData) {
    if (typeof Chart === "undefined") return;

    const gridColor = "rgba(255,255,255,0.07)";
    const textColor = "#8a8a8a";

    const throughputCtx = document.getElementById("throughputChart");
    if (throughputCtx) {
        new Chart(throughputCtx, {
            type: "line",
            data: {
                labels: throughputData.map((d) => d.label),
                datasets: [{
                    data: throughputData.map((d) => d.count),
                    borderColor: "#ffffff",
                    backgroundColor: "rgba(255,255,255,0.06)",
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: "#ffffff",
                    pointRadius: 4,
                    borderWidth: 2,
                }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor, font: { family: "JetBrains Mono", size: 11 } } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: "JetBrains Mono", size: 11 }, precision: 0 }, beginAtZero: true },
                },
            },
        });
    }

    const distributionCtx = document.getElementById("distributionChart");
    if (distributionCtx) {
        new Chart(distributionCtx, {
            type: "bar",
            data: {
                labels: distributionData.map((d) => d.label),
                datasets: [{
                    data: distributionData.map((d) => d.count),
                    backgroundColor: "#ffffff",
                    borderRadius: 2,
                    maxBarThickness: 28,
                }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor, font: { family: "JetBrains Mono", size: 10 }, maxRotation: 40, minRotation: 40 } },
                    y: { grid: { color: gridColor }, ticks: { color: textColor, font: { family: "JetBrains Mono", size: 11 }, precision: 0 }, beginAtZero: true },
                },
            },
        });
    }
}
