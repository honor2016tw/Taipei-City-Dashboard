const state = {
    data: null,
    geojson: null,
    selectedCity: "all",
    selectedUnit: null,
    charts: {},
};

const colorStops = [
    { value: 1.0, color: [120, 212, 107] },
    { value: 1.3, color: [244, 185, 66] },
    { value: 1.6, color: [239, 111, 108] },
    { value: 2.0, color: [177, 78, 223] },
];

document.addEventListener("DOMContentLoaded", async () => {
    if (window.lucide) lucide.createIcons();
    bindCityFilter();
    bindClock();

    try {
        const [data, geojson] = await Promise.all([
            fetch("current_data.json").then((response) => response.json()),
            fetch("metrotaipei_town.geojson").then((response) => response.json()),
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
    renderCharts();
    renderSources();
}

function renderMetrics() {
    const data = state.data;
    document.getElementById("updateTime").textContent = formatDateTime(data.update_time);
    document.getElementById("cbmfValue").textContent = data.amplification ? `${data.amplification.toFixed(2)}x` : "基準中";
    document.getElementById("cbmfDesc").textContent = data.amplification
        ? `目前壓力 / 非雨天同時段基準；${data.unit_count} 個捷運站周邊`
        : "尚無足夠非雨天同時段 baseline，不硬產生倍率";
    document.getElementById("delayValue").textContent = data.current_pressure.toFixed(2);
    document.getElementById("hotspotValue").textContent = `${data.baseline_ready_count} 站`;
    document.getElementById("rainValue").textContent = `${data.avg_rain.toFixed(2)} mm`;
    document.getElementById("weatherTime").textContent = `RainLevel：${data.rain_level}`;
    document.getElementById("timeAxisNote").textContent = `${data.alignment.spatial_unit}；${data.alignment.time_unit}`;
}

function renderCitySummary() {
    const container = document.getElementById("citySummary");
    container.innerHTML = state.data.city_summary
        .map(
            (city) => `
                <article class="city-card">
                    <div>
                        <span>${city.city}平均放大係數</span>
                        <strong>${city.avg_amplification ? `${city.avg_amplification.toFixed(2)}x` : "基準中"}</strong>
                    </div>
                    <div>
                        <span>捷運站周邊 / baseline ready</span>
                        <strong>${city.unit_count} / ${city.baseline_ready_count}</strong>
                    </div>
                    <div class="pill">壓力 ${city.avg_pressure?.toFixed(2) ?? "--"}</div>
                </article>
            `,
        )
        .join("");
}

function renderMap() {
    const svg = document.getElementById("districtMap");
    const bbox = getGeoBounds(state.geojson);
    const units = state.data.units.filter((unit) => state.selectedCity === "all" || unit.city === state.selectedCity);
    if (!state.selectedUnit && state.data.rank_data.length) {
        state.selectedUnit = state.data.rank_data[0].id;
    }

    const outlines = state.geojson.features
        .map((feature) => `<path class="district-outline" d="${geometryToPath(feature.geometry, bbox)}"></path>`)
        .join("");
    const points = units
        .map((unit) => {
            const point = project([unit.lon, unit.lat], bbox);
            const value = unit.amplification || Math.max(1, unit.current_pressure);
            const active = unit.id === state.selectedUnit;
            return `
                <circle
                    class="station-point${active ? " active" : ""}"
                    cx="${point.x.toFixed(1)}"
                    cy="${point.y.toFixed(1)}"
                    r="${active ? 7 : 5}"
                    fill="${scoreColor(value)}"
                    data-unit="${unit.id}"
                    tabindex="0"
                    aria-label="${unit.name} ${unit.amplification ? unit.amplification + 'x' : 'baseline collecting'}"
                ></circle>
            `;
        })
        .join("");

    svg.innerHTML = outlines + points;
    svg.querySelectorAll(".station-point").forEach((node) => {
        const unit = state.data.units.find((item) => item.id === node.dataset.unit);
        node.addEventListener("mousemove", (event) => showTooltip(event, unit));
        node.addEventListener("mouseleave", hideTooltip);
        node.addEventListener("click", () => {
            state.selectedUnit = unit.id;
            renderUnitDetail(unit);
            renderMap();
        });
        node.addEventListener("focus", () => renderUnitDetail(unit));
    });

    renderUnitDetail(state.data.units.find((unit) => unit.id === state.selectedUnit) || state.data.rank_data[0]);
}

function renderUnitDetail(unit) {
    const container = document.getElementById("districtDetail");
    const amp = unit.amplification ? `${unit.amplification.toFixed(2)}x` : "基準中";
    container.innerHTML = `
        <span class="detail-label">${unit.city} · ${unit.town} · ${severityText(unit.severity)}</span>
        <strong>${unit.name}站周邊</strong>
        <p>雨天放大係數 ${amp}；目前壓力 ${unit.current_pressure.toFixed(2)}，baseline ${unit.baseline_pressure?.toFixed(2) ?? "--"}。</p>
        <div class="detail-grid">
            <div><span>降雨 / RainLevel</span><b>${unit.rain_mm.toFixed(2)} mm / ${unit.rain_level}</b></div>
            <div><span>公車 ETA 中位數</span><b>${unit.median_eta_min ?? "--"} 分</b></div>
            <div><span>公車站 / ETA 樣本</span><b>${unit.bus_stop_count} / ${unit.bus_eta_sample_count}</b></div>
            <div><span>YouBike 站</span><b>${unit.bike_station_count}</b></div>
            <div><span>缺車 / 缺位率</span><b>${percent(unit.no_bike_rate)} / ${percent(unit.no_return_rate)}</b></div>
            <div><span>baseline 樣本</span><b>${unit.baseline_samples} · ${baselineText(unit.baseline_status)}</b></div>
        </div>
    `;
}

function renderRankList() {
    const list = document.getElementById("rankList");
    const rows = state.data.units
        .filter((unit) => state.selectedCity === "all" || unit.city === state.selectedCity)
        .sort((a, b) => (b.amplification || b.current_pressure) - (a.amplification || a.current_pressure))
        .slice(0, 10);

    list.innerHTML = rows
        .map(
            (unit, index) => `
                <li>
                    <span class="rank-index">${index + 1}</span>
                    <span class="rank-name">${unit.name}站<span>${unit.city} · 壓力 ${unit.current_pressure.toFixed(2)} · 公車 ${Math.round((unit.contribution.bus || 0) * 100)}% · YouBike ${Math.round((unit.contribution.bike || 0) * 100)}%</span></span>
                    <span class="rank-score">${unit.amplification ? `${unit.amplification.toFixed(2)}x` : "基準中"}</span>
                </li>
            `,
        )
        .join("");
}

function renderCharts() {
    if (!window.Chart) return;
    Chart.defaults.color = "#9ba7b7";
    Chart.defaults.font.family = "Inter, Noto Sans TC, sans-serif";
    const top = [...state.data.units].sort((a, b) => b.current_pressure - a.current_pressure).slice(0, 10);

    state.charts.trend?.destroy();
    state.charts.trend = new Chart(document.getElementById("trendChart"), {
        type: "bar",
        data: {
            labels: top.map((unit) => unit.name),
            datasets: [{ label: "目前通勤壓力", data: top.map((unit) => unit.current_pressure), backgroundColor: "rgba(57, 197, 187, 0.75)" }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" } },
            },
        },
    });

    state.charts.city?.destroy();
    state.charts.city = new Chart(document.getElementById("cityChart"), {
        type: "bar",
        data: {
            labels: state.data.city_summary.map((city) => city.city),
            datasets: [{ label: "平均壓力", data: state.data.city_summary.map((city) => city.avg_pressure), backgroundColor: ["rgba(57, 197, 187, 0.78)", "rgba(244, 185, 66, 0.78)"] }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" } } },
        },
    });
}

function renderSources() {
    document.getElementById("alignmentText").textContent = `${state.data.alignment.spatial_unit}；${state.data.alignment.time_unit}`;
    document.getElementById("formulaText").textContent = state.data.alignment.formula;
    document.getElementById("sourceList").innerHTML = state.data.sources
        .map((source) => `<li><a href="${source.url}" target="_blank" rel="noreferrer">${source.name}</a></li>`)
        .join("");
    document.getElementById("noteList").innerHTML = state.data.notes.map((note) => `<li>${note}</li>`).join("");
}

function getGeoBounds(geojson) {
    const bounds = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
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
                .map((ring) => ring.map((point, index) => `${index ? "L" : "M"}${project(point, bbox).x.toFixed(2)},${project(point, bbox).y.toFixed(2)}`).join(" ") + " Z")
                .join(" "),
        )
        .join(" ");
}

function project(point, bbox) {
    const padding = 34;
    const width = 1000 - padding * 2;
    const height = 820 - padding * 2;
    return {
        x: padding + ((point[0] - bbox.minX) / (bbox.maxX - bbox.minX)) * width,
        y: padding + (1 - (point[1] - bbox.minY) / (bbox.maxY - bbox.minY)) * height,
    };
}

function showTooltip(event, unit) {
    const tooltip = document.getElementById("mapTooltip");
    tooltip.innerHTML = `
        <strong>${unit.name}站</strong><br>
        <span>${unit.city} · ${unit.amplification ? `放大 ${unit.amplification.toFixed(2)}x` : "baseline 累積中"}</span><br>
        壓力 ${unit.current_pressure.toFixed(2)} · 雨 ${unit.rain_mm.toFixed(2)} mm
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
        if (score >= colorStops[index].value) return colorStops[index];
    }
    return colorStops[0];
}

function severityText(value) {
    return {
        collecting: "基準累積中",
        normal: "影響不明顯",
        low: "輕微放大",
        medium: "明顯放大",
        high: "高風險",
        severe: "崩潰熱點",
    }[value] || "觀測中";
}

function baselineText(value) {
    return {
        ready: "歷史基準可用",
        historical: "歷史樣本不足",
        seeded_from_current_dry: "本次非雨快照",
        collecting: "累積中",
    }[value] || value;
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
