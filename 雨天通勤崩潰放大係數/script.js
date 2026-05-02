const state = {
    data: null,
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
    document.getElementById("cbmfValue").textContent = data.amplification ? `${data.amplification.toFixed(2)}x` : "基準中";
    document.getElementById("cbmfDesc").textContent = data.amplification
        ? `RLCAF；${data.unit_count} 個捷運站 500m 接駁圈`
        : "baseline 尚在累積，不硬產生雨天倍率";
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
                        <span>${city.city}平均 RLCAF</span>
                        <strong>${city.avg_amplification ? `${city.avg_amplification.toFixed(2)}x` : "基準中"}</strong>
                    </div>
                    <div>
                        <span>捷運站 / baseline ready</span>
                        <strong>${city.unit_count} / ${city.baseline_ready_count}</strong>
                    </div>
                    <div class="pill">壓力 ${city.avg_pressure?.toFixed(2) ?? "--"}</div>
                </article>
            `,
        )
        .join("");
}

function renderMetroNetwork() {
    const svg = document.getElementById("districtMap");
    const units = state.data.units.filter((unit) => state.selectedCity === "all" || unit.city === state.selectedCity);
    const unitIds = new Set(units.map((unit) => unit.id));
    const bbox = getNetworkBounds(state.data.units);

    if (!state.selectedUnit && state.data.rank_data.length) {
        state.selectedUnit = state.data.rank_data[0].id;
    }

    const lines = state.data.metro_network.lines
        .map((line) => {
            const stations = line.stations.filter((station) => unitIds.has(station.id));
            if (stations.length < 2) return "";
            const d = stations.map((station, index) => {
                const point = project([station.lon, station.lat], bbox);
                return `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`;
            }).join(" ");
            return `<path class="metro-line" d="${d}" stroke="${line.color}" aria-label="${line.id} line"></path>`;
        })
        .join("");

    const points = units
        .map((unit) => {
            const point = project([unit.lon, unit.lat], bbox);
            const value = unit.amplification || Math.max(1, 1 + unit.current_pressure);
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
    const amp = unit.amplification ? `${unit.amplification.toFixed(2)}x` : "基準中";
    container.innerHTML = `
        <span class="detail-label">${unit.city} · ${unit.town} · ${unit.station_type}</span>
        <strong>${unit.name}站接駁圈</strong>
        <p>RLCAF ${amp}；目前壓力 ${unit.current_pressure.toFixed(2)}，baseline ${unit.baseline_pressure?.toFixed(2) ?? "--"}。</p>
        <div class="detail-grid">
            <div><span>降雨 / RainLevel</span><b>${unit.rain_mm.toFixed(2)} mm / ${unit.rain_level}</b></div>
            <div><span>YouBike 取車失敗</span><b>${percent(unit.components.bike_pickup)}</b></div>
            <div><span>YouBike 還車失敗</span><b>${percent(unit.components.bike_return)}</b></div>
            <div><span>公車延誤壓力</span><b>${percent(unit.components.bus_delay)}</b></div>
            <div><span>雨天步行懲罰</span><b>${percent(unit.components.walk_rain)}</b></div>
            <div><span>平均接駁距離</span><b>${unit.avg_transfer_distance_m} m</b></div>
            <div><span>公車 ETA 中位數</span><b>${unit.median_eta_min ?? "--"} 分</b></div>
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
                    <span class="rank-name">${unit.name}站<span>${unit.station_type} · 壓力 ${unit.current_pressure.toFixed(2)} · 取車 ${percent(unit.components.bike_pickup)} · 還車 ${percent(unit.components.bike_return)} · 公車 ${percent(unit.components.bus_delay)}</span></span>
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
            datasets: [
                { label: "取車", data: top.map((unit) => unit.components.bike_pickup), backgroundColor: "rgba(57, 197, 187, 0.78)" },
                { label: "還車", data: top.map((unit) => unit.components.bike_return), backgroundColor: "rgba(244, 185, 66, 0.78)" },
                { label: "公車", data: top.map((unit) => unit.components.bus_delay), backgroundColor: "rgba(239, 111, 108, 0.78)" },
                { label: "步行雨懲罰", data: top.map((unit) => unit.components.walk_rain), backgroundColor: "rgba(126, 161, 255, 0.72)" },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { boxWidth: 10 } } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, beginAtZero: true, max: 4, grid: { color: "rgba(255,255,255,0.06)" } },
            },
        },
    });

    state.charts.city?.destroy();
    state.charts.city = new Chart(document.getElementById("cityChart"), {
        type: "bar",
        data: {
            labels: state.data.city_summary.map((city) => city.city),
            datasets: [{ label: "平均最後一哩壓力", data: state.data.city_summary.map((city) => city.avg_pressure), backgroundColor: ["rgba(57, 197, 187, 0.78)", "rgba(244, 185, 66, 0.78)"] }],
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
    const literature = state.data.literature_basis
        ? `<li>${state.data.literature_basis.summary}</li><li>${state.data.literature_basis.buffer_density_formula}</li><li>${state.data.literature_basis.station_typology}</li>`
        : "";
    document.getElementById("noteList").innerHTML = `${literature}${state.data.notes.map((note) => `<li>${note}</li>`).join("")}`;
}

function getNetworkBounds(units) {
    return units.reduce(
        (bounds, unit) => ({
            minX: Math.min(bounds.minX, unit.lon),
            maxX: Math.max(bounds.maxX, unit.lon),
            minY: Math.min(bounds.minY, unit.lat),
            maxY: Math.max(bounds.maxY, unit.lat),
        }),
        { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity },
    );
}

function project(point, bbox) {
    const padding = 48;
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
        <span>${unit.station_type} · ${unit.amplification ? `RLCAF ${unit.amplification.toFixed(2)}x` : "baseline 累積中"}</span><br>
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
