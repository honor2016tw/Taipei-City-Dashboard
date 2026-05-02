const stops = [
  { value: 0, color: [239, 111, 108] },
  { value: 50, color: [244, 185, 66] },
  { value: 65, color: [126, 161, 255] },
  { value: 80, color: [120, 212, 107] },
  { value: 100, color: [57, 197, 187] },
];

let data;

fetch("../current_data.json")
  .then((response) => response.json())
  .then((payload) => {
    data = payload;
    render();
  });

function render() {
  document.getElementById("metricValue").textContent = scoreText(data.service_score);
  document.getElementById("pressureValue").textContent = `${data.weak_station_count} 站`;
  document.getElementById("baselineValue").textContent = `${data.unit_count} 站`;
  document.getElementById("historyValue").textContent = `${data.history_sample_count || 0} 筆`;
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
  const bounds = getBounds(data.units, data.metro_routes || []);
  const lines = (data.metro_routes || [])
    .map((route) => getRouteLineStrings(route.geometry).map((lineString) => {
      const d = lineString.map((coordinate, index) => {
        const p = project(coordinate, bounds);
        return `${index ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
      }).join(" ");
      return `<path class="metro-line" d="${d}" stroke="${route.color}"></path>`;
    }).join(""))
    .join("");
  const points = data.units.map((unit) => {
    const p = project([unit.lon, unit.lat], bounds);
    return `<circle class="station-point" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="5" fill="${scoreColor(unit.service_score)}" data-id="${unit.id}"></circle>`;
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
    .sort((a, b) => a.service_score - b.service_score)
    .slice(0, 10);
  document.getElementById("rankList").innerHTML = rows.map((unit, index) => `
    <li>
      <span class="rank-index">${index + 1}</span>
      <span class="rank-name">${unit.name}<span>${unit.station_type} · 取車 ${percent(unit.components.bike_pickup)} · 還車 ${percent(unit.components.bike_return)} · 公車 ${percent(unit.components.bus)}</span></span>
      <span class="rank-score">${scoreText(unit.service_score)}</span>
    </li>
  `).join("");
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
  return coordinates.reduce((bounds, coordinate) => ({
    minX: Math.min(bounds.minX, coordinate[0]),
    maxX: Math.max(bounds.maxX, coordinate[0]),
    minY: Math.min(bounds.minY, coordinate[1]),
    maxY: Math.max(bounds.maxY, coordinate[1]),
  }), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });
}

function project(point, bounds) {
  const padding = 34;
  const width = 900 - padding * 2;
  const height = 560 - padding * 2;
  const xSpan = bounds.maxX - bounds.minX || 1;
  const ySpan = bounds.maxY - bounds.minY || 1;
  return {
    x: padding + ((point[0] - bounds.minX) / xSpan) * width,
    y: padding + (1 - (point[1] - bounds.minY) / ySpan) * height,
  };
}

function showTooltip(event, unit) {
  const tooltip = document.getElementById("tooltip");
  tooltip.innerHTML = `<strong>${unit.name}站</strong><br>${unit.station_type}<br>健康度 ${scoreText(unit.service_score)} · 取車 ${percent(unit.components.bike_pickup)} · 公車 ${percent(unit.components.bus)}`;
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
  const t = (score - low.value) / (high.value - low.value || 1);
  return rgb(low.color.map((channel, index) => Math.round(channel + (high.color[index] - channel) * t)));
}

function lowerStop(score) {
  for (let index = stops.length - 1; index >= 0; index -= 1) {
    if (score >= stops[index].value) return stops[index];
  }
  return stops[0];
}

function scoreText(value) {
  return Number.isFinite(value) ? Math.round(value).toString() : "--";
}

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function rgb(parts) {
  return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`;
}
