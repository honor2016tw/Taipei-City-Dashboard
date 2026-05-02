const state = {
    data: null,
    selectedCity: "all",
    selectedUnit: null,
    charts: {},
};

const colorStops = [
    { value: 0, color: [239, 111, 108] },
    { value: 50, color: [244, 185, 66] },
    { value: 65, color: [126, 161, 255] },
    { value: 80, color: [120, 212, 107] },
    { value: 100, color: [57, 197, 187] },
];

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) lucide.createIcons();
    bindCityFilter();
    bindClock();

    try {
        state.data = await fetch("current_data.json").then((response) => response.json());
        renderDashboard();
    } catch (error) {
        console.error(error);
        document.getElementById("cbmfDesc").textContent = "資料載入失敗，請先執行 python3 update_data.py。";
    }
});

function bindClock() {
    setInterval(() => {
        if (!state.data) return;
        document.getElementById("updateTime").textContent = formatDateTime(state.data.update_time);
    }, 30000);
}

function bindCityFilter() {
    document.querySelectorAll("[data-city]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-city]").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            state.selectedCity = button.dataset.city;
            renderMetroNetwork();
            renderRankList();
        });
    });
}

function renderDashboard() {
    renderMetrics();
    renderCitySummary();
    renderMetroNetwork();
    renderRankList();
    renderCharts();
    renderSources();
}

function renderMetrics() {
    const data = state.data;
    document.getElementById("updateTime").textContent = formatDateTime(data.update_time);
    document.getElementById("cbmfValue").textContent = scoreText(data.service_score);
    document.getElementById("cbmfDesc").textContent = `${data.metric_short_name}；${data.unit_count} 個捷運站 500m 接駁圈`;
    document.getElementById("delayValue").textContent = `${data.weak_station_count} 站`;
    document.getElementById("hotspotValue").textContent = `${data.unit_count} 站`;
    document.getElementById("rainValue").textContent = `${data.history_sample_count || 0} 筆`;
    document.getElementById("weatherTime").textContent = "歷史快照用於趨勢觀察";
    document.getElementById("timeAxisNote").textContent = `${data.alignment.spatial_unit}；${data.alignment.time_unit}`;
}

function renderCitySummary() {
    const container = document.getElementById("citySummary");
    container.innerHTML = state.data.city_summary
        .map(
            (city) => `
                <article class="city-card">
                    <div>
                        <span>${city.city}平均健康度</span>
                        <strong>${scoreText(city.avg_service_score)}</strong>
                    </div>
                    <div>
                        <span>捷運站 / 弱服務站</span>
                        <strong>${city.unit_count} / ${city.weak_station_count}</strong>
                    </div>
                    <div class="pill">${healthText(city.avg_service_score)}</div>
                </article>
            `,
        )
        .join("");
}

function renderMetroNetwork() {
    const svg = document.getElementById("districtMap");
    const units = state.data.units.filter((unit) => state.selectedCity === "all" || unit.city === state.selectedCity);
    const routes = state.data.metro_routes || [];
    const bbox = getBounds(units, routes);

    if (!state.selectedUnit && state.data.rank_data.length) {
        state.selectedUnit = state.data.rank_data[0].id;
    }

    const lines = routes
        .map((route) =>
            getRouteLineStrings(route.geometry)
                .map((lineString) => {
                    const d = lineString
                        .map((coordinate, index) => {
                            const point = project(coordinate, bbox, 1000, 820, 48);
                            return `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`;
                        })
                        .join(" ");
                    return `<path class="metro-line" d="${d}" stroke="${route.color}" aria-label="${route.name}"></path>`;
                })
                .join(""),
        )
        .join("");

    const points = units
        .map((unit) => {
            const point = project([unit.lon, unit.lat], bbox, 1000, 820, 48);
            const active = unit.id === state.selectedUnit;
            return `
                <circle
                    class="station-point${active ? " active" : ""}"
                    cx="${point.x.toFixed(1)}"
                    cy="${point.y.toFixed(1)}"
                    r="${active ? 7 : 5}"
                    fill="${scoreColor(unit.service_score)}"
                    data-unit="${unit.id}"
                    tabindex="0"
                    aria-label="${unit.name} 健康度 ${unit.service_score}"
                ></circle>
            `;
        })
        .join("");

    svg.innerHTML = lines + points;
    svg.querySelectorAll(".station-point").forEach((node) => {
        const unit = state.data.units.find((item) => item.id === node.dataset.unit);
        node.addEventListener("mousemove", (event) => showTooltip(event, unit));
        node.addEventListener("mouseleave", hideTooltip);
        node.addEventListener("click", () => {
            state.selectedUnit = unit.id;
            renderUnitDetail(unit);
            renderMetroNetwork();
        });
        node.addEventListener("focus", () => renderUnitDetail(unit));
    });

    renderUnitDetail(state.data.units.find((unit) => unit.id === state.selectedUnit) || state.data.rank_data[0]);
}

function renderUnitDetail(unit) {
    const container = document.getElementById("districtDetail");
    if (!unit) {
        container.innerHTML = "<strong>沒有站點資料</strong>";
        return;
    }
    container.innerHTML = `
        <span class="detail-label">${unit.city} · ${unit.town || "未標示行政區"} · ${unit.station_type}</span>
        <strong>${unit.name}站最後一哩</strong>
        <p>服務健康度 ${scoreText(unit.service_score)}；${healthText(unit.service_score)}。分數越低，代表出站後 YouBike 或公車接駁越可能失效。</p>
        <div class="detail-grid">
            <div><span>YouBike 取車可用</span><b>${percent(unit.components.bike_pickup)}</b></div>
            <div><span>YouBike 還車可用</span><b>${percent(unit.components.bike_return)}</b></div>
            <div><span>公車即時可靠</span><b>${percent(unit.components.bus)}</b></div>
            <div><span>替代接駁覆蓋</span><b>${percent(unit.components.coverage)}</b></div>
            <div><span>YouBike 站 / 車 / 位</span><b>${unit.bike_station_count} / ${unit.available_rent_bikes} / ${unit.available_return_bikes}</b></div>
            <div><span>公車站 / ETA 樣本</span><b>${unit.bus_stop_count} / ${unit.bus_eta_sample_count}</b></div>
            <div><span>公車 ETA 中位數</span><b>${unit.median_eta_min ?? "--"} 分</b></div>
            <div><span>公車異常率</span><b>${percent(unit.bus_issue_rate)}</b></div>
        </div>
    `;
}

function renderRankList() {
    const list = document.getElementById("rankList");
    const rows = state.data.units
        .filter((unit) => state.selectedCity === "all" || unit.city === state.selectedCity)
        .sort((a, b) => a.service_score - b.service_score)
        .slice(0, 10);

    list.innerHTML = rows
        .map(
            (unit, index) => `
                <li>
                    <span class="rank-index">${index + 1}</span>
                    <span class="rank-name">${unit.name}站<span>${unit.station_type} · 取車 ${percent(unit.components.bike_pickup)} · 還車 ${percent(unit.components.bike_return)} · 公車 ${percent(unit.components.bus)} · 覆蓋 ${percent(unit.components.coverage)}</span></span>
                    <span class="rank-score">${scoreText(unit.service_score)}</span>
                </li>
            `,
        )
        .join("");
}

function renderCharts() {
    if (!window.Chart) return;
    Chart.defaults.color = "#9ba7b7";
    Chart.defaults.font.family = "Inter, Noto Sans TC, sans-serif";
    const weakest = [...state.data.units].sort((a, b) => a.service_score - b.service_score).slice(0, 10);

    state.charts.trend?.destroy();
    state.charts.trend = new Chart(document.getElementById("trendChart"), {
        type: "bar",
        data: {
            labels: weakest.map((unit) => unit.name),
            datasets: [
                { label: "取車", data: weakest.map((unit) => unit.components.bike_pickup * 100), backgroundColor: "rgba(57, 197, 187, 0.78)" },
                { label: "還車", data: weakest.map((unit) => unit.components.bike_return * 100), backgroundColor: "rgba(244, 185, 66, 0.78)" },
                { label: "公車", data: weakest.map((unit) => unit.components.bus * 100), backgroundColor: "rgba(239, 111, 108, 0.78)" },
                { label: "覆蓋", data: weakest.map((unit) => unit.components.coverage * 100), backgroundColor: "rgba(126, 161, 255, 0.72)" },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { boxWidth: 10 } } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, beginAtZero: true, max: 400, grid: { color: "rgba(255,255,255,0.06)" } },
            },
        },
    });

    state.charts.city?.destroy();
    state.charts.city = new Chart(document.getElementById("cityChart"), {
        type: "bar",
        data: {
            labels: state.data.city_summary.map((city) => city.city),
            datasets: [{ label: "平均服務健康度", data: state.data.city_summary.map((city) => city.avg_service_score), backgroundColor: ["rgba(57, 197, 187, 0.78)", "rgba(244, 185, 66, 0.78)"] }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, max: 100, grid: { color: "rgba(255,255,255,0.06)" } } },
        },
    });
}

function renderSources() {
    document.getElementById("alignmentText").textContent = `${state.data.alignment.spatial_unit}；${state.data.alignment.time_unit}`;
    document.getElementById("formulaText").textContent = state.data.alignment.formula;
    document.getElementById("sourceList").innerHTML = state.data.sources
        .map((source) => `<li><a href="${source.url}" target="_blank" rel="noreferrer">${source.name}</a></li>`)
        .join("");
    const literature = state.data.literature_basis
        ? `<li>${state.data.literature_basis.summary}</li><li>${state.data.literature_basis.buffer_density_formula}</li><li>${state.data.literature_basis.station_typology}</li>`
        : "";
    document.getElementById("noteList").innerHTML = `${literature}${state.data.notes.map((note) => `<li>${note}</li>`).join("")}`;
}

function getRouteLineStrings(geometry) {
    if (!geometry) return [];
    if (geometry.type === "LineString") return [geometry.coordinates];
    if (geometry.type === "MultiLineString") return geometry.coordinates;
    return [];
}

function getBounds(units, routes) {
    const coordinates = [];
    units.forEach((unit) => coordinates.push([unit.lon, unit.lat]));
    routes.forEach((route) => {
        getRouteLineStrings(route.geometry).forEach((lineString) => {
            lineString.forEach((coordinate) => coordinates.push(coordinate));
        });
    });
    return coordinates.reduce(
        (bounds, coordinate) => ({
            minX: Math.min(bounds.minX, coordinate[0]),
            maxX: Math.max(bounds.maxX, coordinate[0]),
            minY: Math.min(bounds.minY, coordinate[1]),
            maxY: Math.max(bounds.maxY, coordinate[1]),
        }),
        { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity },
    );
}

function project(point, bbox, canvasWidth, canvasHeight, padding) {
    const width = canvasWidth - padding * 2;
    const height = canvasHeight - padding * 2;
    const xSpan = bbox.maxX - bbox.minX || 1;
    const ySpan = bbox.maxY - bbox.minY || 1;
    return {
        x: padding + ((point[0] - bbox.minX) / xSpan) * width,
        y: padding + (1 - (point[1] - bbox.minY) / ySpan) * height,
    };
}

function showTooltip(event, unit) {
    const tooltip = document.getElementById("mapTooltip");
    tooltip.innerHTML = `
        <strong>${unit.name}站</strong><br>
        <span>${unit.station_type} · 健康度 ${scoreText(unit.service_score)}</span><br>
        取車 ${percent(unit.components.bike_pickup)} · 還車 ${percent(unit.components.bike_return)} · 公車 ${percent(unit.components.bus)}
    `;
    tooltip.style.display = "block";
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
}

function hideTooltip() {
    document.getElementById("mapTooltip").style.display = "none";
}

function scoreColor(score) {
    const low = findLowerColorStop(score);
    const high = colorStops.find((stop) => score <= stop.value) || colorStops[colorStops.length - 1];
    if (low === high) return rgb(low.color);
    const t = (score - low.value) / (high.value - low.value || 1);
    return rgb(low.color.map((channel, index) => Math.round(channel + (high.color[index] - channel) * t)));
}

function findLowerColorStop(score) {
    for (let index = colorStops.length - 1; index >= 0; index -= 1) {
        if (score >= colorStops[index].value) return colorStops[index];
    }
    return colorStops[0];
}

function healthText(score) {
    if (score >= 80) return "服務穩定";
    if (score >= 65) return "需觀察";
    if (score >= 50) return "服務偏弱";
    return "接駁失效風險高";
}

function scoreText(value) {
    return Number.isFinite(value) ? Math.round(value).toString() : "--";
}

function percent(value) {
    return `${Math.round((value || 0) * 100)}%`;
}

function formatDateTime(value) {
    if (!value) return "無資料";
    return new Intl.DateTimeFormat("zh-TW", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

function rgb(parts) {
    return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`;
}
