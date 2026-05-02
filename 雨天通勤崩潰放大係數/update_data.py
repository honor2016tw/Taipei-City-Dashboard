import json
import math
import os
import ssl
import statistics
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "current_data.json")
HISTORY_FILE = os.path.join(BASE_DIR, "pressure_history.jsonl")

TDX_TOKEN_URL = "https://apiatis.ntpc.gov.tw/ntpc-api/TDX/Token"
TDX_METRO_STATIONS = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC?$format=JSON"
TDX_BIKE_STATION = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/{city}?$format=JSON"
TDX_BIKE_AVAILABILITY = "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/{city}?$format=JSON"
TDX_BUS_STOPS = "https://tdx.transportdata.tw/api/basic/v2/Bus/Stop/City/{city}?$format=JSON"
TDX_BUS_ETA = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city}?$format=JSON"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

STATION_RADIUS_M = 500
BASELINE_MIN_SAMPLES = 3
METHOD_VERSION = "rlcaf_v2"

LINE_COLORS = {
    "BR": "#c48c31",
    "R": "#e3002c",
    "G": "#008659",
    "O": "#f8b61c",
    "BL": "#0070bd",
    "Y": "#ffdb00",
    "LG": "#a6a6a6",
}

COMPONENT_WEIGHTS = {
    "bike_pickup": 0.25,
    "bike_return": 0.25,
    "bus_delay": 0.25,
    "walk_rain": 0.15,
    "road_interference": 0.10,
}


def fetch_json(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "codefest-cbmf/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))


def get_tdx_headers():
    token_payload = fetch_json(TDX_TOKEN_URL)
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("TDX token response does not include token")
    return {"Authorization": f"Bearer {token}", "User-Agent": "codefest-cbmf/2.0"}


def city_short(value):
    if value in ("臺北市", "台北市", "Taipei", "TPE"):
        return "臺北"
    if value in ("新北市", "NewTaipei", "NWT"):
        return "新北"
    return value or "未知"


def haversine_m(lon1, lat1, lon2, lat2):
    radius = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_station_order(station_id):
    suffix = "".join(char for char in station_id if char.isdigit() or char.isalpha())
    digits = "".join(char for char in suffix if char.isdigit())
    letters = "".join(char for char in suffix if char.isalpha())
    base = int(digits) if digits else 0
    branch = 0.5 if letters.endswith("A") else 0
    return base + branch


def fetch_metro_assets(headers):
    rows = fetch_json(TDX_METRO_STATIONS, headers=headers)
    seen = {}
    line_groups = {}
    for row in rows:
        pos = row.get("StationPosition") or {}
        name = row.get("StationName", {}).get("Zh_tw")
        lon = pos.get("PositionLon")
        lat = pos.get("PositionLat")
        if not name or lon is None or lat is None:
            continue
        station_id = row.get("StationID", "")
        line = station_id[:2] if station_id[:2] in LINE_COLORS else station_id[:1]
        key = name
        if key in seen:
            seen[key]["lon_values"].append(float(lon))
            seen[key]["lat_values"].append(float(lat))
            seen[key]["lines"].append(line)
        else:
            city = city_short(row.get("LocationCity") or row.get("LocationCityCode"))
            if city not in ("臺北", "新北"):
                continue
            seen[key] = {
                "id": f"TRTC-{name}",
                "name": name,
                "city": city,
                "town": row.get("LocationTown") or "",
                "lon_values": [float(lon)],
                "lat_values": [float(lat)],
                "lines": [line],
            }
        if line:
            line_groups.setdefault(line, []).append(
                {
                    "name": name,
                    "order": parse_station_order(station_id),
                    "lon": float(lon),
                    "lat": float(lat),
                    "station_id": station_id,
                }
            )

    units = []
    unit_by_name = {}
    for item in seen.values():
        item["lon"] = statistics.mean(item.pop("lon_values"))
        item["lat"] = statistics.mean(item.pop("lat_values"))
        item["lines"] = sorted(set(line for line in item["lines"] if line))
        item["network_degree"] = len(item["lines"])
        units.append(item)
        unit_by_name[item["name"]] = item

    lines = []
    for line, stations in line_groups.items():
        unique = {}
        for station in stations:
            unique.setdefault(station["name"], station)
        ordered = sorted(unique.values(), key=lambda station: station["order"])
        lines.append(
            {
                "id": line,
                "color": LINE_COLORS.get(line, "#8a94a6"),
                "stations": [
                    {
                        "id": unit_by_name[station["name"]]["id"],
                        "name": station["name"],
                        "lon": round(unit_by_name[station["name"]]["lon"], 6),
                        "lat": round(unit_by_name[station["name"]]["lat"], 6),
                        "order": station["order"],
                    }
                    for station in ordered
                    if station["name"] in unit_by_name
                ],
            }
        )
    return units, {"lines": sorted(lines, key=lambda line: line["id"])}


def fetch_bike_city(city, headers):
    stations = fetch_json(TDX_BIKE_STATION.format(city=city), headers=headers)
    availability = fetch_json(TDX_BIKE_AVAILABILITY.format(city=city), headers=headers)
    live_by_uid = {item["StationUID"]: item for item in availability}
    rows = []
    for station in stations:
        live = live_by_uid.get(station["StationUID"])
        pos = station.get("StationPosition") or {}
        if not live or pos.get("PositionLon") is None or pos.get("PositionLat") is None:
            continue
        rows.append(
            {
                "uid": station["StationUID"],
                "name": station.get("StationName", {}).get("Zh_tw", station["StationUID"]),
                "city": city_short(city),
                "lon": float(pos["PositionLon"]),
                "lat": float(pos["PositionLat"]),
                "capacity": int(station.get("BikesCapacity") or 0),
                "rent": int(live.get("AvailableRentBikes") or 0),
                "return": int(live.get("AvailableReturnBikes") or 0),
                "service": int(live.get("ServiceStatus") or 0),
                "update_time": live.get("UpdateTime"),
            }
        )
    return rows


def fetch_bus_city(city, headers):
    stops = fetch_json(TDX_BUS_STOPS.format(city=city), headers=headers)
    eta = fetch_json(TDX_BUS_ETA.format(city=city), headers=headers)
    stop_by_uid = {}
    for stop in stops:
        pos = stop.get("StopPosition") or {}
        if pos.get("PositionLon") is None or pos.get("PositionLat") is None:
            continue
        stop_by_uid[stop["StopUID"]] = {
            "uid": stop["StopUID"],
            "name": stop.get("StopName", {}).get("Zh_tw", stop["StopUID"]),
            "city": city_short(stop.get("LocationCityCode") or city),
            "lon": float(pos["PositionLon"]),
            "lat": float(pos["PositionLat"]),
            "eta_seconds": [],
            "status_total": 0,
            "status_bad": 0,
            "update_times": [],
        }
    for item in eta:
        stop = stop_by_uid.get(item.get("StopUID"))
        if not stop:
            continue
        stop["status_total"] += 1
        if item.get("StopStatus") != 0:
            stop["status_bad"] += 1
        estimate = item.get("EstimateTime")
        if isinstance(estimate, int) and 0 <= estimate <= 3600:
            stop["eta_seconds"].append(estimate)
        if item.get("UpdateTime"):
            stop["update_times"].append(item["UpdateTime"])
    return list(stop_by_uid.values())


def fetch_weather(units):
    weather = []
    for start in range(0, len(units), 50):
        chunk = units[start : start + 50]
        params = {
            "latitude": ",".join(f'{unit["lat"]:.5f}' for unit in chunk),
            "longitude": ",".join(f'{unit["lon"]:.5f}' for unit in chunk),
            "current": "precipitation,rain,weather_code",
            "hourly": "precipitation",
            "past_days": "1",
            "forecast_days": "1",
            "timezone": "Asia/Taipei",
        }
        payload = fetch_json(OPEN_METEO_URL + "?" + urllib.parse.urlencode(params))
        weather.extend(payload if isinstance(payload, list) else [payload])
    return weather


def nearby(items, unit, radius_m=STATION_RADIUS_M):
    lat_delta = radius_m / 111320
    lon_delta = radius_m / (111320 * max(0.2, math.cos(math.radians(unit["lat"]))))
    return [
        item
        for item in items
        if item["city"] == unit["city"]
        and abs(item["lat"] - unit["lat"]) <= lat_delta
        and abs(item["lon"] - unit["lon"]) <= lon_delta
        and haversine_m(unit["lon"], unit["lat"], item["lon"], item["lat"]) <= radius_m
    ]


def bike_failure_score(stations):
    if not stations:
        return {
            "pickup_failure": 0,
            "return_failure": 0,
            "bike_station_count": 0,
            "no_bike_rate": 0,
            "no_return_rate": 0,
            "offline_rate": 0,
        }
    bike_ratios = [station["rent"] / station["capacity"] for station in stations if station["capacity"] > 0]
    dock_ratios = [station["return"] / station["capacity"] for station in stations if station["capacity"] > 0]
    pickup_failure = 1 - min(1, statistics.median(bike_ratios)) if bike_ratios else 0
    return_failure = 1 - min(1, statistics.median(dock_ratios)) if dock_ratios else 0
    no_bike = len([station for station in stations if station["rent"] <= 2]) / len(stations)
    no_return = len([station for station in stations if station["return"] <= 2]) / len(stations)
    offline = len([station for station in stations if station["service"] != 1]) / len(stations)
    return {
        "pickup_failure": round(min(1, pickup_failure + 0.15 * offline), 3),
        "return_failure": round(min(1, return_failure + 0.15 * offline), 3),
        "bike_station_count": len(stations),
        "no_bike_rate": round(no_bike, 3),
        "no_return_rate": round(no_return, 3),
        "offline_rate": round(offline, 3),
        "available_rent_bikes": sum(station["rent"] for station in stations),
        "available_return_bikes": sum(station["return"] for station in stations),
    }


def bus_delay_score(stops):
    active = [stop for stop in stops if stop["eta_seconds"]]
    if not stops:
        return 0, {"bus_stop_count": 0, "median_eta_min": None, "bus_issue_rate": 0}
    all_eta = [seconds / 60 for stop in active for seconds in stop["eta_seconds"]]
    median_eta = statistics.median(all_eta) if all_eta else None
    issue_total = sum(stop["status_total"] for stop in stops)
    issue_bad = sum(stop["status_bad"] for stop in stops)
    issue_rate = issue_bad / issue_total if issue_total else 0
    eta_score = min(1, (median_eta or 20) / 20)
    bus_score = min(1, 0.75 * eta_score + 0.25 * issue_rate)
    return bus_score, {
        "bus_stop_count": len(stops),
        "bus_eta_sample_count": len(all_eta),
        "median_eta_min": round(median_eta, 1) if median_eta is not None else None,
        "bus_issue_rate": round(issue_rate, 3),
    }


def rain_level(mm):
    if mm >= 15:
        return 4
    if mm >= 7.5:
        return 3
    if mm >= 2.5:
        return 2
    if mm >= 0.5:
        return 1
    return 0


def current_weather(weather):
    all_times = weather["hourly"]["time"]
    now_hour = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
    if now_hour in all_times:
        idx = all_times.index(now_hour)
    else:
        idx = min(range(len(all_times)), key=lambda index: abs(datetime.fromisoformat(all_times[index]) - datetime.now()))
    rain = float(weather.get("current", {}).get("precipitation") or weather["hourly"]["precipitation"][idx] or 0)
    return rain, idx, all_times


def rain_intensity_score(rain_mm):
    return min(1, rain_mm / 10)


def avg_transfer_distance(unit, bikes_nearby, stops_nearby):
    points = bikes_nearby + stops_nearby
    if not points:
        return STATION_RADIUS_M
    return statistics.mean(haversine_m(unit["lon"], unit["lat"], point["lon"], point["lat"]) for point in points)


def walk_rain_penalty(rain_mm, avg_distance_m):
    return round(min(1, rain_intensity_score(rain_mm) * (avg_distance_m / STATION_RADIUS_M)), 3)


def commute_pressure(components):
    available = {
        key: value
        for key, value in components.items()
        if isinstance(value, (int, float)) and key in COMPONENT_WEIGHTS
    }
    weight_sum = sum(COMPONENT_WEIGHTS[key] for key in available)
    if weight_sum == 0:
        return 0
    return round(sum(available[key] * COMPONENT_WEIGHTS[key] for key in available) / weight_sum, 3)


def component_contribution(components):
    weighted = {
        key: value * COMPONENT_WEIGHTS[key]
        for key, value in components.items()
        if isinstance(value, (int, float)) and key in COMPONENT_WEIGHTS
    }
    total = sum(weighted.values()) or 1
    return {key: round(value / total, 3) for key, value in weighted.items()}


def classify_station(unit, bike_detail, bus_detail):
    if unit["network_degree"] >= 2:
        return "轉乘型站"
    if bus_detail["bus_stop_count"] >= 45 and bike_detail["bike_station_count"] >= 4:
        return "通勤型站"
    if bike_detail["bike_station_count"] >= 8:
        return "商圈混合型站"
    if bus_detail["bus_stop_count"] <= 12 and bike_detail["bike_station_count"] <= 2:
        return "郊區型站"
    return "一般接駁型站"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    rows = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        for line in file:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def baseline_for(unit_id, now, history, current_pressure=None, current_rain_level=None):
    samples = [
        row["pressure"]
        for row in history
        if row.get("unit_id") == unit_id
        and row.get("method_version") == METHOD_VERSION
        and row.get("weekday") == now.weekday()
        and row.get("hour") == now.hour
        and row.get("rain_level") == 0
    ]
    status = "historical"
    if not samples and current_rain_level == 0 and current_pressure is not None:
        samples = [current_pressure]
        status = "seeded_from_current_dry"
    if not samples:
        return None, 0, "collecting"
    return round(statistics.median(samples), 3), len(samples), status if len(samples) < BASELINE_MIN_SAMPLES else "ready"


def append_history(rows, now):
    with open(HISTORY_FILE, "a", encoding="utf-8") as file:
        for row in rows:
            file.write(
                json.dumps(
                    {
                        "time": now.isoformat(timespec="seconds"),
                        "method_version": METHOD_VERSION,
                        "unit_id": row["id"],
                        "weekday": now.weekday(),
                        "hour": now.hour,
                        "rain_level": row["rain_level"],
                        "pressure": row["current_pressure"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def build_result():
    now = datetime.now().astimezone()
    headers = get_tdx_headers()
    units, metro_network = fetch_metro_assets(headers)
    bikes = fetch_bike_city("Taipei", headers) + fetch_bike_city("NewTaipei", headers)
    bus_stops = fetch_bus_city("Taipei", headers) + fetch_bus_city("NewTaipei", headers)
    weather_points = fetch_weather(units)
    history = load_history()

    rows = []
    for unit, weather in zip(units, weather_points):
        rain_mm, current_idx, all_times = current_weather(weather)
        bikes_nearby = nearby(bikes, unit)
        stops_nearby = nearby(bus_stops, unit)
        bike_detail = bike_failure_score(bikes_nearby)
        bus_score, bus_detail = bus_delay_score(stops_nearby)
        transfer_distance = avg_transfer_distance(unit, bikes_nearby, stops_nearby)
        components = {
            "bike_pickup": bike_detail["pickup_failure"],
            "bike_return": bike_detail["return_failure"],
            "bus_delay": bus_score,
            "walk_rain": walk_rain_penalty(rain_mm, transfer_distance),
            "road_interference": None,
        }
        pressure = commute_pressure(components)
        level = rain_level(rain_mm)
        baseline, sample_count, baseline_status = baseline_for(unit["id"], now, history, pressure, level)
        amplification = round(pressure / baseline, 2) if baseline and baseline > 0 else None
        contribution = component_contribution(components)
        station_type = classify_station(unit, bike_detail, bus_detail)
        rows.append(
            {
                "id": unit["id"],
                "name": unit["name"],
                "city": unit["city"],
                "town": unit["town"],
                "lon": round(unit["lon"], 6),
                "lat": round(unit["lat"], 6),
                "lines": sorted(set(line for line in unit["lines"] if line)),
                "network_degree": unit["network_degree"],
                "station_type": station_type,
                "rain_mm": round(rain_mm, 2),
                "rain_level": level,
                "current_pressure": pressure,
                "baseline_pressure": baseline,
                "baseline_samples": sample_count,
                "baseline_status": baseline_status,
                "amplification": amplification,
                "severity": severity(amplification),
                "components": components,
                "contribution": contribution,
                "avg_transfer_distance_m": round(transfer_distance),
                **bike_detail,
                **bus_detail,
            }
        )

    append_history(rows, now)
    scored = [row for row in rows if row["amplification"] is not None]
    ranking_key = lambda row: row["amplification"] if row["amplification"] is not None else row["current_pressure"]
    rank_data = sorted(rows, key=ranking_key, reverse=True)[:10]
    city_summary = []
    for city in ("臺北", "新北"):
        group = [row for row in rows if row["city"] == city]
        scored_group = [row for row in group if row["amplification"] is not None]
        city_summary.append(
            {
                "city": city,
                "unit_count": len(group),
                "avg_amplification": round(statistics.mean(row["amplification"] for row in scored_group), 2)
                if scored_group
                else None,
                "avg_pressure": round(statistics.mean(row["current_pressure"] for row in group), 2) if group else None,
                "baseline_ready_count": len([row for row in group if row["baseline_status"] == "ready"]),
            }
        )

    avg_amplification = round(statistics.mean(row["amplification"] for row in scored), 2) if scored else None
    avg_pressure = round(statistics.mean(row["current_pressure"] for row in rows), 2)
    return {
        "metric_name": "雨天通勤崩潰放大係數",
        "unit_name": "捷運站周邊",
        "radius_m": STATION_RADIUS_M,
        "amplification": avg_amplification,
        "current_pressure": avg_pressure,
        "baseline_ready_count": len([row for row in rows if row["baseline_status"] == "ready"]),
        "unit_count": len(rows),
        "avg_rain": round(statistics.mean(row["rain_mm"] for row in rows), 2),
        "rain_level": max(row["rain_level"] for row in rows),
        "update_time": now.isoformat(timespec="seconds"),
        "city_summary": city_summary,
        "rank_data": rank_data,
        "units": rows,
        "metro_network": metro_network,
        "alignment": {
            "spatial_unit": f"捷運站周邊 {STATION_RADIUS_M} 公尺",
            "time_unit": "即時交通壓力；baseline 為同星期、同時段、非雨天本機歷史快照中位數",
            "formula": "RLCAF(s,t) = RainLastMilePressure(s,t) / NonRainBaselinePressure(s,dow,time_slot)",
        },
        "component_weights": COMPONENT_WEIGHTS,
        "literature_basis": {
            "catchment_radius_m": STATION_RADIUS_M,
            "summary": "參考共享單車作為捷運最後一哩補充工具的研究，MVP 採 500m 捷運站影響範圍；正式版可用雙北 YouBike 歷史旅次重算 buffer 邊際密度轉折點。",
            "buffer_density_formula": "increase_Den_j = (D_{j+1} - D_j) / [pi * (R_{j+1}^2 - R_j^2)]",
            "station_typology": "MVP 以轉乘線數、公車站密度與 YouBike 站密度做規則式站型；正式版可用 hourly trips features + K-means + silhouette coefficient。",
        },
        "sources": [
            {"name": "TDX TRTC Metro Station", "url": TDX_METRO_STATIONS},
            {"name": "TDX Bus Stop / EstimatedTimeOfArrival - Taipei", "url": TDX_BUS_ETA.format(city="Taipei")},
            {"name": "TDX Bus Stop / EstimatedTimeOfArrival - NewTaipei", "url": TDX_BUS_ETA.format(city="NewTaipei")},
            {"name": "TDX YouBike Station/Availability - Taipei", "url": TDX_BIKE_STATION.format(city="Taipei")},
            {"name": "TDX YouBike Station/Availability - NewTaipei", "url": TDX_BIKE_STATION.format(city="NewTaipei")},
            {"name": "Open-Meteo Forecast API precipitation", "url": "https://open-meteo.com/"},
        ],
        "notes": [
            "本版主指標改為 Rain-induced Last-mile Collapse Amplification Factor：目前最後一哩壓力除以同星期、同時段、非雨天 baseline。",
            "目前最後一哩壓力由 YouBike 取車失敗、YouBike 還車失敗、公車延誤、雨天步行懲罰組成；道路干擾保留欄位但不以缺資料硬估。",
            "若 baseline 樣本不足，頁面會顯示基準累積中，不硬產生看似精準的雨天倍率。",
            "雨量目前使用 Open-Meteo 逐時降雨；若接上雨量站 10/30/60 分鐘資料，可直接替換 RainLevel 與 walk_rain。",
        ],
    }


def severity(amplification):
    if amplification is None:
        return "collecting"
    if amplification > 2:
        return "severe"
    if amplification >= 1.6:
        return "high"
    if amplification >= 1.3:
        return "medium"
    if amplification >= 1.1:
        return "low"
    return "normal"


def main():
    data = build_result()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(
        "Data saved: "
        f"units={data['unit_count']} pressure={data['current_pressure']} amplification={data['amplification']}"
    )


if __name__ == "__main__":
    main()
