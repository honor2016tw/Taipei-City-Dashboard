const state = {
    data: null,
    geojson: null,
    selectedCity: "all",
    selectedDistrict: null,
    charts: {},
};

const colorStops = [
    { value: 1.0, color: [120, 212, 107] },
    { value: 1.45, color: [244, 185, 66] },
    { value: 2.1, color: [239, 111, 108] },
];

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) {
        lucide.createIcons();
    }

    bindCityFilter();
    bindClock();

    try {
        const [data, geojson] = await Promise.all([
            fetch("current_data.json").then((response) => response.json()),
            fetch("../Taipei-City-Dashboard-FE/public/mapData/metrotaipei_town.geojson").then((response) => response.json()),
        ]);
        state.data = data;
        state.geojson = geojson;
        renderDashboard();
    } catch (error) {
        console.error(error);
        document.getElementById("cbmfDesc").textContent = "資料載入失敗，請先執行 python3 update_data.py。";
    }
});

function bindClock() {
    setInterval(() => {
        const update = document.getElementById("updateTime");
        if (!state.data) return;
        update.textContent = formatDateTime(state.data.update_time);
    }, 30000);
}

function bindCityFilter() {
    document.querySelectorAll("[data-city]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-city]").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            state.selectedCity = button.dataset.city;
            renderMap();
            renderRankList();
        });
    });
}

function renderDashboard() {
    renderMetrics();
    renderCitySummary();
    renderMap();
    renderRankList();
    try {
        renderCharts();
    } catch (error) {
        console.warn("Chart rendering fallback", error);
        renderFallbackCharts();
    }
    renderSources();
}

function renderMetrics() {
    const data = state.data;
    document.getElementById("updateTime").textContent = formatDateTime(data.update_time);
    document.getElementById("cbmfValue").textContent = `${data.cbmf.toFixed(2)}x`;
    document.getElementById("cbmfDesc").textContent = `全域平均比基準通勤壓力高 ${Math.round((data.cbmf - 1) * 100)}%`;
    document.getElementById("delayValue").textContent = `${data.delay} 分`;
    document.getElementById("hotspotValue").textContent = `${data.hotspots} 區`;
    document.getElementById("rainValue").textContent = `${data.avg_rain.toFixed(2)} mm`;
    document.getElementById("weatherTime").textContent = `降雨時間：${data.data_time.weather_hour}`;
    document.getElementById("timeAxisNote").textContent = `${data.alignment.spatial_unit}；${data.alignment.time_unit}`;
}

function renderCitySummary() {
    const container = document.getElementById("citySummary");
    container.innerHTML = state.data.city_summary
        .map((city) => {
            const lowRate = city.bike_station_count
                ? Math.round((city.low_bike_station_count / city.bike_station_count) * 100)
                : 0;
            return `
                <article class="city-card">
                    <div>
                        <span>${city.city}平均 CBMF</span>
                        <strong>${city.cbmf.toFixed(2)}x</strong>
                    </div>
                    <div>
                        <span>行政區 / YouBike 站</span>
                        <strong>${city.district_count} / ${city.bike_station_count}</strong>
                    </div>
                    <div class="pill">${lowRate}% 低可用站</div>
                </article>
            `;
        })
        .join("");
}

function renderMap() {
    const svg = document.getElementById("districtMap");
    const rowsByName = new Map(state.data.districts.map((row) => [row.name, row]));
    const bbox = getGeoBounds(state.geojson);
    const paths = [];

    if (!state.selectedDistrict) {
        state.selectedDistrict = state.data.rank_data[0].name;
    }

    state.geojson.features.forEach((feature) => {
        const name = feature.properties.TNAME;
        const row = rowsByName.get(name);
        if (!row) return;
        const d = geometryToPath(feature.geometry, bbox);
        const dimmed = state.selectedCity !== "all" && row.city !== state.selectedCity;
        const active = state.selectedDistrict === name;
        paths.push(`
            <path
                class="district-path${dimmed ? " dimmed" : ""}${active ? " active" : ""}"
                d="${d}"
                fill="${scoreColor(row.cbmf)}"
                data-district="${name}"
                tabindex="0"
                aria-label="${name} CBMF ${row.cbmf}"
            ></path>
        `);
    });

    svg.innerHTML = paths.join("");
    svg.querySelectorAll(".district-path").forEach((path) => {
        const district = path.dataset.district;
        const row = rowsByName.get(district);
        path.addEventListener("mousemove", (event) => showTooltip(event, row));
        path.addEventListener("mouseleave", hideTooltip);
        path.addEventListener("click", () => {
            state.selectedDistrict = district;
            renderDistrictDetail(row);
            renderMap();
        });
        path.addEventListener("focus", () => renderDistrictDetail(row));
    });

    renderDistrictDetail(rowsByName.get(state.selectedDistrict) || state.data.rank_data[0]);
}

function getGeoBounds(geojson) {
    const bounds = {
        minX: Infinity,
        maxX: -Infinity,
        minY: Infinity,
        maxY: -Infinity,
    };
    geojson.features.forEach((feature) => {
        visitCoordinates(feature.geometry.coordinates, (point) => {
            bounds.minX = Math.min(bounds.minX, point[0]);
            bounds.maxX = Math.max(bounds.maxX, point[0]);
            bounds.minY = Math.min(bounds.minY, point[1]);
            bounds.maxY = Math.max(bounds.maxY, point[1]);
        });
    });
    return bounds;
}

function visitCoordinates(coordinates, callback) {
    if (typeof coordinates[0] === "number") {
        callback(coordinates);
        return;
    }
    coordinates.forEach((item) => visitCoordinates(item, callback));
}

function geometryToPath(geometry, bbox) {
    const polygons = geometry.type === "MultiPolygon" ? geometry.coordinates : [geometry.coordinates];
    return polygons
        .map((polygon) =>
            polygon
                .map((ring) =>
                    ring
                        .map((point, index) => {
                            const projected = project(point, bbox);
                            return `${index === 0 ? "M" : "L"}${projected.x.toFixed(2)},${projected.y.toFixed(2)}`;
                        })
                        .join(" ") + " Z",
                )
                .join(" "),
        )
        .join(" ");
}

function project(point, bbox) {
    const padding = 34;
    const width = 1000 - padding * 2;
    const height = 820 - padding * 2;
    const x = padding + ((point[0] - bbox.minX) / (bbox.maxX - bbox.minX)) * width;
    const y = padding + (1 - (point[1] - bbox.minY) / (bbox.maxY - bbox.minY)) * height;
    return { x, y };
}

function renderDistrictDetail(row) {
    const fullRow = state.data.districts.find((district) => district.name === row.name) || row;
    const container = document.getElementById("districtDetail");
    container.innerHTML = `
        <span class="detail-label">${fullRow.city} · ${severityText(fullRow.severity)}</span>
        <strong>${fullRow.name}</strong>
        <p>CBMF ${fullRow.cbmf.toFixed(2)}x，估計延遲 ${fullRow.delay_min} 分鐘。</p>
        <div class="detail-grid">
            <div><span>降雨</span><b>${fullRow.rain_mm.toFixed(2)} mm</b></div>
            <div><span>YouBike 壓力</span><b>${Math.round(fullRow.bike_stress * 100)}%</b></div>
            <div><span>可借 / 可還</span><b>${fullRow.available_rent_bikes} / ${fullRow.available_return_bikes}</b></div>
            <div><span>低可用站</span><b>${fullRow.low_bike_station_count} / ${fullRow.bike_station_count}</b></div>
        </div>
    `;
}

function renderRankList() {
    const list = document.getElementById("rankList");
    const rows = state.data.districts
        .filter((row) => state.selectedCity === "all" || row.city === state.selectedCity)
        .sort((a, b) => b.cbmf - a.cbmf)
        .slice(0, 10);

    list.innerHTML = rows
        .map(
            (row, index) => `
                <li>
                    <span class="rank-index">${index + 1}</span>
                    <span class="rank-name">${row.name}<span>${row.city} · 雨 ${row.rain_mm.toFixed(2)} mm · YouBike 壓力 ${Math.round(row.bike_stress * 100)}%</span></span>
                    <span class="rank-score">${row.cbmf.toFixed(2)}x</span>
                </li>
            `,
        )
        .join("");
}

function renderCharts() {
    if (!window.Chart) {
        renderFallbackCharts();
        return;
    }

    Chart.defaults.color = "#9ba7b7";
    Chart.defaults.font.family = "Inter, Noto Sans TC, sans-serif";

    const trendCtx = document.getElementById("trendChart");
    state.charts.trend?.destroy();
    state.charts.trend = new Chart(trendCtx, {
        type: "line",
        data: {
            labels: state.data.trend_labels,
            datasets: [
                {
                    label: "雙北平均 CBMF",
                    data: state.data.trend_values,
                    borderColor: "#39c5bb",
                    backgroundColor: "rgba(57, 197, 187, 0.14)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (item) => `CBMF ${item.formattedValue}x` } },
            },
            scales: {
                x: { grid: { color: "rgba(255,255,255,0.05)" } },
                y: { min: 1, grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: (value) => `${value}x` } },
            },
        },
    });

    const cityCtx = document.getElementById("cityChart");
    state.charts.city?.destroy();
    state.charts.city = new Chart(cityCtx, {
        type: "bar",
        data: {
            labels: state.data.city_summary.map((city) => city.city),
            datasets: [
                {
                    label: "CBMF",
                    data: state.data.city_summary.map((city) => city.cbmf),
                    backgroundColor: ["rgba(57, 197, 187, 0.78)", "rgba(244, 185, 66, 0.78)"],
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { min: 1, grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: (value) => `${value}x` } },
            },
        },
    });
}

function renderFallbackCharts() {
    renderFallbackTrend();
    renderFallbackCityBars();
}

function renderFallbackTrend() {
    const canvas = document.getElementById("trendChart");
    const values = state.data.trend_values;
    const labels = state.data.trend_labels;
    const min = Math.min(...values, 1);
    const max = Math.max(...values, 1.4);
    const points = values.map((value, index) => {
        const x = 44 + (index / Math.max(values.length - 1, 1)) * 680;
        const y = 268 - ((value - min) / Math.max(max - min, 0.01)) * 218;
        return { x, y, value, label: labels[index] };
    });
    const line = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
    const area = `${line} L724,292 L44,292 Z`;

    canvas.style.display = "none";
    canvas.parentElement.querySelector(".fallback-chart")?.remove();
    canvas.parentElement.insertAdjacentHTML(
        "beforeend",
        `<svg class="fallback-chart" viewBox="0 0 760 320" role="img" aria-label="雙北平均 CBMF 趨勢">
            <line x1="44" y1="292" x2="724" y2="292"></line>
            <line x1="44" y1="48" x2="44" y2="292"></line>
            <path class="chart-area" d="${area}"></path>
            <path class="chart-line" d="${line}"></path>
            ${points
                .map(
                    (point) => `
                        <g>
                            <circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="4"></circle>
                            <title>${point.label}: ${point.value.toFixed(2)}x</title>
                        </g>
                    `,
                )
                .join("")}
            <text x="44" y="30">${max.toFixed(2)}x</text>
            <text x="44" y="314">${min.toFixed(2)}x</text>
        </svg>`,
    );
}

function renderFallbackCityBars() {
    const canvas = document.getElementById("cityChart");
    const max = Math.max(...state.data.city_summary.map((city) => city.cbmf), 1.4);
    canvas.style.display = "none";
    canvas.parentElement.querySelector(".fallback-chart")?.remove();
    canvas.parentElement.insertAdjacentHTML(
        "beforeend",
        `<div class="fallback-bars" role="img" aria-label="臺北與新北平均 CBMF 比較">
            ${state.data.city_summary
                .map((city) => {
                    const height = Math.max(12, (city.cbmf / max) * 210);
                    return `
                        <div class="fallback-bar">
                            <div class="bar-track"><span style="height: ${height}px"></span></div>
                            <strong>${city.cbmf.toFixed(2)}x</strong>
                            <small>${city.city}</small>
                        </div>
                    `;
                })
                .join("")}
        </div>`,
    );
}

function renderSources() {
    document.getElementById("alignmentText").textContent = `${state.data.alignment.spatial_unit}；${state.data.alignment.time_unit}`;
    document.getElementById("formulaText").textContent = state.data.alignment.formula;
    document.getElementById("sourceList").innerHTML = state.data.sources
        .map((source) => `<li><a href="${source.url}" target="_blank" rel="noreferrer">${source.name}</a></li>`)
        .join("");
    document.getElementById("noteList").innerHTML = state.data.notes.map((note) => `<li>${note}</li>`).join("");
}

function showTooltip(event, row) {
    const tooltip = document.getElementById("mapTooltip");
    tooltip.innerHTML = `
        <strong>${row.name}</strong><br>
        <span>${row.city} · CBMF ${row.cbmf.toFixed(2)}x</span><br>
        雨 ${row.rain_mm.toFixed(2)} mm · YouBike 壓力 ${Math.round(row.bike_stress * 100)}%
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
    const t = (score - low.value) / (high.value - low.value);
    return rgb(low.color.map((channel, index) => Math.round(channel + (high.color[index] - channel) * t)));
}

function findLowerColorStop(score) {
    for (let index = colorStops.length - 1; index >= 0; index -= 1) {
        if (score >= colorStops[index].value) {
            return colorStops[index];
        }
    }
    return colorStops[0];
}

function rgb(parts) {
    return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`;
}

function severityText(severity) {
    return {
        severe: "嚴重",
        high: "高壓",
        medium: "注意",
        normal: "正常",
    }[severity] || "正常";
}

function formatDateTime(value) {
    if (!value) return "--";
    const date = new Date(value);
    return new Intl.DateTimeFormat("zh-TW", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}
