const stops = [
  { value: 1.0, color: [120, 212, 107] },
  { value: 1.3, color: [244, 185, 66] },
  { value: 1.6, color: [239, 111, 108] },
  { value: 2.0, color: [177, 78, 223] },
];

let data;

fetch("../current_data.json")
  .then((response) => response.json())
  .then((payload) => {
    data = payload;
    render();
  });

function render() {
  document.getElementById("metricValue").textContent = data.amplification ? `${data.amplification.toFixed(2)}x` : "基準中";
  document.getElementById("pressureValue").textContent = data.current_pressure.toFixed(2);
  document.getElementById("baselineValue").textContent = `${data.baseline_ready_count} / ${data.unit_count}`;
  document.getElementById("rainValue").textContent = `${data.avg_rain.toFixed(2)} mm`;
  document.getElementById("updateValue").textContent = new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(data.update_time));
  renderNetwork();
  renderRank();
  document.getElementById("methodText").textContent = `${data.alignment.formula}；${data.literature_basis.summary}`;
}

function renderNetwork() {
  const svg = document.getElementById("networkSvg");
  const bounds = getBounds(data.units);
  const lines = data.metro_network.lines
    .map((line) => {
      if (line.stations.length < 2) return "";
      const d = line.stations.map((station, index) => {
        const p = project([station.lon, station.lat], bounds);
        return `${index ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
      }).join(" ");
      return `<path class="metro-line" d="${d}" stroke="${line.color}"></path>`;
    })
    .join("");
  const points = data.units.map((unit) => {
    const p = project([unit.lon, unit.lat], bounds);
    const value = unit.amplification || Math.max(1, 1 + unit.current_pressure);
    return `<circle class="station-point" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="5" fill="${scoreColor(value)}" data-id="${unit.id}"></circle>`;
  }).join("");
  svg.innerHTML = lines + points;
  svg.querySelectorAll(".station-point").forEach((node) => {
    const unit = data.units.find((item) => item.id === node.dataset.id);
    node.addEventListener("mousemove", (event) => showTooltip(event, unit));
    node.addEventListener("mouseleave", hideTooltip);
  });
}

function renderRank() {
  const rows = [...data.units]
    .sort((a, b) => (b.amplification || b.current_pressure) - (a.amplification || a.current_pressure))
    .slice(0, 10);
  document.getElementById("rankList").innerHTML = rows.map((unit, index) => `
    <li>
      <span class="rank-index">${index + 1}</span>
      <span class="rank-name">${unit.name}<span>${unit.station_type} · 取車 ${percent(unit.components.bike_pickup)} · 還車 ${percent(unit.components.bike_return)} · 公車 ${percent(unit.components.bus_delay)}</span></span>
      <span class="rank-score">${unit.amplification ? `${unit.amplification.toFixed(2)}x` : "基準中"}</span>
    </li>
  `).join("");
}

function getBounds(units) {
  return units.reduce((bounds, unit) => ({
    minX: Math.min(bounds.minX, unit.lon),
    maxX: Math.max(bounds.maxX, unit.lon),
    minY: Math.min(bounds.minY, unit.lat),
    maxY: Math.max(bounds.maxY, unit.lat),
  }), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });
}

function project(point, bounds) {
  const padding = 34;
  const width = 900 - padding * 2;
  const height = 560 - padding * 2;
  return {
    x: padding + ((point[0] - bounds.minX) / (bounds.maxX - bounds.minX)) * width,
    y: padding + (1 - (point[1] - bounds.minY) / (bounds.maxY - bounds.minY)) * height,
  };
}

function showTooltip(event, unit) {
  const tooltip = document.getElementById("tooltip");
  tooltip.innerHTML = `<strong>${unit.name}站</strong><br>${unit.station_type}<br>壓力 ${unit.current_pressure.toFixed(2)} · 雨 ${unit.rain_mm.toFixed(2)} mm`;
  tooltip.style.display = "block";
  tooltip.style.left = `${event.clientX + 12}px`;
  tooltip.style.top = `${event.clientY + 12}px`;
}

function hideTooltip() {
  document.getElementById("tooltip").style.display = "none";
}

function scoreColor(score) {
  const low = lowerStop(score);
  const high = stops.find((stop) => score <= stop.value) || stops[stops.length - 1];
  if (low === high) return rgb(low.color);
  const t = (score - low.value) / (high.value - low.value);
  return rgb(low.color.map((channel, index) => Math.round(channel + (high.color[index] - channel) * t)));
}

function lowerStop(score) {
  for (let index = stops.length - 1; index >= 0; index -= 1) {
    if (score >= stops[index].value) return stops[index];
  }
  return stops[0];
}

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function rgb(parts) {
  return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`;
}
