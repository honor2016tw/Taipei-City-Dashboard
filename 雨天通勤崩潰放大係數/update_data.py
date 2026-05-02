import json
import math
import os
import ssl
import statistics
import urllib.error
import urllib.request
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "current_data.json")
HISTORY_FILE = os.path.join(BASE_DIR, "last_mile_service_history.jsonl")
ROUTE_DIR = os.path.join(BASE_DIR, "metro_routes")

TDX_TOKEN_URL = "https://apiatis.ntpc.gov.tw/ntpc-api/TDX/Token"
TDX_METRO_STATIONS = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC?$format=JSON"
TDX_BIKE_STATION = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/{city}?$format=JSON"
TDX_BIKE_AVAILABILITY = "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/{city}?$format=JSON"
TDX_BUS_STOPS = "https://tdx.transportdata.tw/api/basic/v2/Bus/Stop/City/{city}?$format=JSON"
TDX_BUS_ETA = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city}?$format=JSON"

STATION_RADIUS_M = 500
METHOD_VERSION = "last_mile_service_v1"

LINE_COLORS = {
    "BR": "#c48c31",
    "R": "#e3002c",
    "G": "#008659",
    "O": "#f8b61c",
    "BL": "#0070bd",
}

ROUTE_FILES = [
    "metro_bl_line_car_route.geojson",
    "metro_br_line_car_route.geojson",
    "metro_g_line_car_route.geojson",
    "metro_g_line_car_route_2.geojson",
    "metro_o_line_car_route.geojson",
    "metro_o_line_car_route_2.geojson",
    "metro_r_line_car_route.geojson",
    "metro_r_line_car_route_2.geojson",
]

WEIGHTS = {
    "bike_pickup": 0.30,
    "bike_return": 0.25,
    "bus": 0.30,
    "coverage": 0.15,
}


def fetch_json(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "codefest-last-mile/1.0"})
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
    return {"Authorization": f"Bearer {token}", "User-Agent": "codefest-last-mile/1.0"}


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


def parse_line(station_id):
    station_id = (station_id or "").upper()
    if station_id.startswith("BL"):
        return "BL"
    if station_id.startswith("BR"):
        return "BR"
    if station_id.startswith("R"):
        return "R"
    if station_id.startswith("G"):
        return "G"
    if station_id.startswith("O"):
        return "O"
    return ""


def fetch_metro_stations(headers):
    rows = fetch_json(TDX_METRO_STATIONS, headers=headers)
    seen = {}
    for row in rows:
        pos = row.get("StationPosition") or {}
        name = row.get("StationName", {}).get("Zh_tw")
        lon = pos.get("PositionLon")
        lat = pos.get("PositionLat")
        if not name or lon is None or lat is None:
            continue
        city = city_short(row.get("LocationCity") or row.get("LocationCityCode"))
        if city not in ("臺北", "新北"):
            continue
        line = parse_line(row.get("StationID", ""))
        if name not in seen:
            seen[name] = {
                "id": f"TRTC-{name}",
                "name": name,
                "city": city,
                "town": row.get("LocationTown") or "",
                "lon_values": [],
                "lat_values": [],
                "lines": [],
            }
        seen[name]["lon_values"].append(float(lon))
        seen[name]["lat_values"].append(float(lat))
        if line:
            seen[name]["lines"].append(line)

    stations = []
    for station in seen.values():
        station["lon"] = statistics.mean(station.pop("lon_values"))
        station["lat"] = statistics.mean(station.pop("lat_values"))
        station["lines"] = sorted(set(station["lines"]))
        station["network_degree"] = len(station["lines"])
        stations.append(station)
    return stations


def load_metro_routes():
    routes = []
    for filename in ROUTE_FILES:
        path = os.path.join(ROUTE_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as file:
            geojson = json.load(file)
        feature = geojson["features"][0]
        line_id = feature.get("properties", {}).get("mrtid") or filename.split("_")[1].upper()
        routes.append(
            {
                "id": line_id,
                "name": feature.get("properties", {}).get("mrtcode") or line_id,
                "color": LINE_COLORS.get(line_id, "#8a94a6"),
                "geometry": feature["geometry"],
            }
        )
    return routes


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


def bike_scores(stations):
    if not stations:
        return {
            "bike_station_count": 0,
            "pickup_score": 0,
            "return_score": 0,
            "bike_offline_rate": 0,
            "available_rent_bikes": 0,
            "available_return_bikes": 0,
        }
    rent_ratios = [station["rent"] / station["capacity"] for station in stations if station["capacity"] > 0]
    return_ratios = [station["return"] / station["capacity"] for station in stations if station["capacity"] > 0]
    offline_rate = len([station for station in stations if station["service"] != 1]) / len(stations)
    pickup = min(1, statistics.median(rent_ratios)) if rent_ratios else 0
    returns = min(1, statistics.median(return_ratios)) if return_ratios else 0
    return {
        "bike_station_count": len(stations),
        "pickup_score": round(max(0, pickup - 0.2 * offline_rate), 3),
        "return_score": round(max(0, returns - 0.2 * offline_rate), 3),
        "bike_offline_rate": round(offline_rate, 3),
        "available_rent_bikes": sum(station["rent"] for station in stations),
        "available_return_bikes": sum(station["return"] for station in stations),
    }


def bus_scores(stops):
    if not stops:
        return {
            "bus_stop_count": 0,
            "bus_eta_sample_count": 0,
            "median_eta_min": None,
            "bus_issue_rate": 0,
            "bus_score": 0,
        }
    all_eta = [seconds / 60 for stop in stops for seconds in stop["eta_seconds"]]
    median_eta = statistics.median(all_eta) if all_eta else None
    issue_total = sum(stop["status_total"] for stop in stops)
    issue_bad = sum(stop["status_bad"] for stop in stops)
    issue_rate = issue_bad / issue_total if issue_total else 0
    eta_score = max(0, 1 - ((median_eta or 20) / 25))
    bus_score = max(0, min(1, 0.72 * eta_score + 0.28 * (1 - issue_rate)))
    return {
        "bus_stop_count": len(stops),
        "bus_eta_sample_count": len(all_eta),
        "median_eta_min": round(median_eta, 1) if median_eta is not None else None,
        "bus_issue_rate": round(issue_rate, 3),
        "bus_score": round(bus_score, 3),
    }


def coverage_score(bike_count, bus_count):
    bike_part = min(1, bike_count / 6)
    bus_part = min(1, bus_count / 35)
    return round(0.45 * bike_part + 0.55 * bus_part, 3)


def service_status(score):
    if score >= 80:
        return "good"
    if score >= 65:
        return "watch"
    if score >= 50:
        return "weak"
    return "failing"


def station_type(unit, bike_count, bus_count):
    if unit["network_degree"] >= 2:
        return "轉乘型站"
    if bus_count >= 45 and bike_count >= 4:
        return "通勤型站"
    if bike_count >= 8:
        return "商圈混合型站"
    if bus_count <= 12 and bike_count <= 2:
        return "郊區型站"
    return "一般接駁型站"


def load_recent_history(limit=2000):
    if not os.path.exists(HISTORY_FILE):
        return []
    rows = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        for line in file:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def append_history(rows, now):
    with open(HISTORY_FILE, "a", encoding="utf-8") as file:
        for row in rows:
            file.write(
                json.dumps(
                    {
                        "time": now.isoformat(timespec="seconds"),
                        "method_version": METHOD_VERSION,
                        "unit_id": row["id"],
                        "service_score": row["service_score"],
                        "pickup_score": row["components"]["bike_pickup"],
                        "return_score": row["components"]["bike_return"],
                        "bus_score": row["components"]["bus"],
                        "coverage_score": row["components"]["coverage"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def build_result():
    now = datetime.now().astimezone()
    headers = get_tdx_headers()
    units = fetch_metro_stations(headers)
    routes = load_metro_routes()
    bikes = fetch_bike_city("Taipei", headers) + fetch_bike_city("NewTaipei", headers)
    bus_stops = fetch_bus_city("Taipei", headers) + fetch_bus_city("NewTaipei", headers)

    rows = []
    for unit in units:
        bikes_nearby = nearby(bikes, unit)
        stops_nearby = nearby(bus_stops, unit)
        bike = bike_scores(bikes_nearby)
        bus = bus_scores(stops_nearby)
        coverage = coverage_score(bike["bike_station_count"], bus["bus_stop_count"])
        components = {
            "bike_pickup": bike["pickup_score"],
            "bike_return": bike["return_score"],
            "bus": bus["bus_score"],
            "coverage": coverage,
        }
        service_score_raw = sum(components[key] * WEIGHTS[key] for key in components)
        service_score = round(service_score_raw * 100)
        risk_score = round(100 - service_score)
        rows.append(
            {
                "id": unit["id"],
                "name": unit["name"],
                "city": unit["city"],
                "town": unit["town"],
                "lon": round(unit["lon"], 6),
                "lat": round(unit["lat"], 6),
                "lines": unit["lines"],
                "network_degree": unit["network_degree"],
                "station_type": station_type(unit, bike["bike_station_count"], bus["bus_stop_count"]),
                "service_score": service_score,
                "risk_score": risk_score,
                "service_status": service_status(service_score),
                "components": components,
                **bike,
                **bus,
            }
        )

    append_history(rows, now)
    history = load_recent_history()
    city_summary = []
    for city in ("臺北", "新北"):
        group = [row for row in rows if row["city"] == city]
        city_summary.append(
            {
                "city": city,
                "unit_count": len(group),
                "avg_service_score": round(statistics.mean(row["service_score"] for row in group), 1) if group else None,
                "weak_station_count": len([row for row in group if row["service_score"] < 65]),
            }
        )

    return {
        "metric_name": "捷運最後一哩服務健康度",
        "metric_short_name": "Last-mile Service Health",
        "unit_name": "捷運站周邊",
        "radius_m": STATION_RADIUS_M,
        "service_score": round(statistics.mean(row["service_score"] for row in rows), 1),
        "weak_station_count": len([row for row in rows if row["service_score"] < 65]),
        "unit_count": len(rows),
        "update_time": now.isoformat(timespec="seconds"),
        "city_summary": city_summary,
        "rank_data": sorted(rows, key=lambda row: row["service_score"])[:10],
        "units": rows,
        "metro_routes": routes,
        "history_sample_count": len(history),
        "component_weights": WEIGHTS,
        "alignment": {
            "spatial_unit": f"捷運站周邊 {STATION_RADIUS_M} 公尺",
            "time_unit": "即時 YouBike / 公車 ETA 快照",
            "formula": "ServiceHealth = 100 * (0.30*BikePickup + 0.25*BikeReturn + 0.30*Bus + 0.15*Coverage)",
        },
        "sources": [
            {"name": "TDX TRTC Metro Station", "url": TDX_METRO_STATIONS},
            {"name": "TDX Bus Stop / EstimatedTimeOfArrival - Taipei", "url": TDX_BUS_ETA.format(city="Taipei")},
            {"name": "TDX Bus Stop / EstimatedTimeOfArrival - NewTaipei", "url": TDX_BUS_ETA.format(city="NewTaipei")},
            {"name": "TDX YouBike Station/Availability - Taipei", "url": TDX_BIKE_STATION.format(city="Taipei")},
            {"name": "TDX YouBike Station/Availability - NewTaipei", "url": TDX_BIKE_STATION.format(city="NewTaipei")},
            {"name": "Taipei City Dashboard metro route GeoJSON", "url": "metro_routes/*.geojson"},
        ],
        "notes": [
            "本版主指標聚焦即時最後一哩服務健康度，不再以雨天或歷史 baseline 作為主要判斷。",
            "服務健康度衡量捷運站 500 公尺接駁圈內 YouBike 取車、還車、公車 ETA 與替代接駁覆蓋是否足夠。",
            "捷運路網使用城市儀表板既有 metro route GeoJSON，不再用站點排序硬連線。",
            "歷史檔用於觀察服務健康度趨勢；若未來要重新做雨天版本，可再把降雨作為情境濾鏡。",
        ],
    }


def main():
    data = build_result()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(
        "Data saved: "
        f"units={data['unit_count']} service={data['service_score']} weak={data['weak_station_count']}"
    )


if __name__ == "__main__":
    main()
