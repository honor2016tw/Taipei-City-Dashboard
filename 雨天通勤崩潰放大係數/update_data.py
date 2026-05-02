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
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
DISTRICT_GEOJSON = os.path.join(
    ROOT_DIR, "Taipei-City-Dashboard-FE", "public", "mapData", "metrotaipei_town.geojson"
)
OUTPUT_FILE = os.path.join(BASE_DIR, "current_data.json")

TAIPEI_DISTRICTS = {
    "北投區",
    "士林區",
    "內湖區",
    "南港區",
    "松山區",
    "信義區",
    "中山區",
    "大同區",
    "中正區",
    "萬華區",
    "大安區",
    "文山區",
}

TDX_TOKEN_URL = "https://apiatis.ntpc.gov.tw/ntpc-api/TDX/Token"
TDX_BIKE_STATION = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/{city}?$format=JSON"
TDX_BIKE_AVAILABILITY = "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/{city}?$format=JSON"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "codefest-cbmf/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))


def flatten_rings(geometry):
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        rings = []
        for polygon in geometry["coordinates"]:
            rings.extend(polygon)
        return rings
    return []


def polygon_centroid(ring):
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring
    if not points:
        return None
    area = 0
    cx = 0
    cy = 0
    for i, point in enumerate(points):
        x1, y1 = point[0], point[1]
        x2, y2 = points[(i + 1) % len(points)][0], points[(i + 1) % len(points)][1]
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area) < 0.0000001:
        return {
            "lon": sum(point[0] for point in points) / len(points),
            "lat": sum(point[1] for point in points) / len(points),
        }
    area *= 0.5
    return {"lon": cx / (6 * area), "lat": cy / (6 * area)}


def point_in_ring(lon, lat, ring):
    inside = False
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring
    j = len(points) - 1
    for i, point in enumerate(points):
        xi, yi = point[0], point[1]
        xj, yj = points[j][0], points[j][1]
        intersects = (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def point_in_geometry(lon, lat, geometry):
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return False

    for polygon in polygons:
        outer = polygon[0]
        holes = polygon[1:]
        if point_in_ring(lon, lat, outer) and not any(point_in_ring(lon, lat, hole) for hole in holes):
            return True
    return False


def load_districts():
    with open(DISTRICT_GEOJSON, "r", encoding="utf-8") as file:
        geojson = json.load(file)

    districts = []
    for feature in geojson["features"]:
        props = feature["properties"]
        rings = flatten_rings(feature["geometry"])
        centroid = polygon_centroid(max(rings, key=len))
        districts.append(
            {
                "name": props["TNAME"],
                "city": props["PNAME"],
                "city_short": "臺北" if props["TNAME"] in TAIPEI_DISTRICTS else "新北",
                "centroid": centroid,
                "geometry": feature["geometry"],
            }
        )
    return districts


def get_tdx_headers():
    token_payload = fetch_json(TDX_TOKEN_URL)
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("TDX token response does not include token")
    return {"Authorization": f"Bearer {token}", "User-Agent": "codefest-cbmf/1.0"}


def fetch_bike_city(city, headers):
    stations = fetch_json(TDX_BIKE_STATION.format(city=city), headers=headers)
    availability = fetch_json(TDX_BIKE_AVAILABILITY.format(city=city), headers=headers)
    availability_by_uid = {item["StationUID"]: item for item in availability}
    merged = []
    for station in stations:
        live = availability_by_uid.get(station["StationUID"])
        if not live:
            continue
        pos = station.get("StationPosition", {})
        merged.append(
            {
                "uid": station["StationUID"],
                "name": station.get("StationName", {}).get("Zh_tw", station["StationUID"]),
                "lon": float(pos.get("PositionLon", 0)),
                "lat": float(pos.get("PositionLat", 0)),
                "capacity": int(station.get("BikesCapacity") or 0),
                "rent": int(live.get("AvailableRentBikes") or 0),
                "return": int(live.get("AvailableReturnBikes") or 0),
                "service": int(live.get("ServiceStatus") or 0),
                "src_update_time": live.get("SrcUpdateTime"),
                "update_time": live.get("UpdateTime"),
            }
        )
    return merged


def assign_bikes_to_districts(districts, bikes):
    district_stats = {
        district["name"]: {
            "bike_station_count": 0,
            "bike_capacity": 0,
            "available_rent_bikes": 0,
            "available_return_bikes": 0,
            "low_bike_station_count": 0,
            "offline_station_count": 0,
            "bike_update_times": [],
        }
        for district in districts
    }

    for station in bikes:
        matched = None
        for district in districts:
            if point_in_geometry(station["lon"], station["lat"], district["geometry"]):
                matched = district["name"]
                break
        if not matched:
            continue

        stats = district_stats[matched]
        stats["bike_station_count"] += 1
        stats["bike_capacity"] += station["capacity"]
        stats["available_rent_bikes"] += station["rent"]
        stats["available_return_bikes"] += station["return"]
        if station["service"] != 1:
            stats["offline_station_count"] += 1
        if station["rent"] <= 2 or station["return"] <= 2:
            stats["low_bike_station_count"] += 1
        if station["update_time"]:
            stats["bike_update_times"].append(station["update_time"])

    return district_stats


def fetch_weather(districts):
    latitudes = ",".join(f'{district["centroid"]["lat"]:.5f}' for district in districts)
    longitudes = ",".join(f'{district["centroid"]["lon"]:.5f}' for district in districts)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "current": "precipitation,rain,weather_code",
        "hourly": "precipitation",
        "past_days": "1",
        "forecast_days": "1",
        "timezone": "Asia/Taipei",
    }
    url = OPEN_METEO_URL + "?" + urllib.parse.urlencode(params)
    payload = fetch_json(url)
    return payload if isinstance(payload, list) else [payload]


def calc_bike_stress(stats):
    station_count = stats["bike_station_count"]
    if station_count == 0 or stats["bike_capacity"] == 0:
        return 0
    rent_ratio = stats["available_rent_bikes"] / stats["bike_capacity"]
    return_ratio = stats["available_return_bikes"] / stats["bike_capacity"]
    imbalance = min(1, abs(rent_ratio - return_ratio) * 1.4)
    low_station_rate = stats["low_bike_station_count"] / station_count
    offline_rate = stats["offline_station_count"] / station_count
    return min(1, 0.55 * low_station_rate + 0.3 * imbalance + 0.15 * offline_rate)


def calc_cbmf(rain_mm, bike_stress):
    rain_stress = min(1.6, rain_mm / 10)
    return round(1 + 0.62 * rain_stress + 0.58 * bike_stress, 2)


def severity(cbmf):
    if cbmf >= 2:
        return "severe"
    if cbmf >= 1.55:
        return "high"
    if cbmf >= 1.25:
        return "medium"
    return "normal"


def build_result():
    districts = load_districts()
    headers = get_tdx_headers()
    bike_stations = fetch_bike_city("Taipei", headers) + fetch_bike_city("NewTaipei", headers)
    bike_stats = assign_bikes_to_districts(districts, bike_stations)
    weather_points = fetch_weather(districts)

    all_times = weather_points[0]["hourly"]["time"]
    now_hour = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
    if now_hour in all_times:
        current_idx = all_times.index(now_hour)
    else:
        current_idx = min(range(len(all_times)), key=lambda index: abs(datetime.fromisoformat(all_times[index]) - datetime.now()))
    trend_indexes = list(range(max(0, current_idx - 11), current_idx + 1))
    time_axis = [all_times[index] for index in trend_indexes]

    district_rows = []
    city_groups = {"臺北": [], "新北": []}
    bike_update_times = []

    for district, weather in zip(districts, weather_points):
        stats = bike_stats[district["name"]]
        hourly_rain = weather["hourly"]["precipitation"]
        current_rain = float(weather.get("current", {}).get("precipitation") or hourly_rain[current_idx] or 0)
        bike_stress = calc_bike_stress(stats)
        cbmf = calc_cbmf(current_rain, bike_stress)
        row = {
            "name": district["name"],
            "city": district["city_short"],
            "lon": round(district["centroid"]["lon"], 6),
            "lat": round(district["centroid"]["lat"], 6),
            "cbmf": cbmf,
            "severity": severity(cbmf),
            "rain_mm": round(current_rain, 2),
            "bike_stress": round(bike_stress, 3),
            "bike_station_count": stats["bike_station_count"],
            "bike_capacity": stats["bike_capacity"],
            "available_rent_bikes": stats["available_rent_bikes"],
            "available_return_bikes": stats["available_return_bikes"],
            "low_bike_station_count": stats["low_bike_station_count"],
            "offline_station_count": stats["offline_station_count"],
            "delay_min": round((cbmf - 1) * 28),
            "trend_values": [calc_cbmf(float(hourly_rain[index] or 0), bike_stress) for index in trend_indexes],
        }
        district_rows.append(row)
        city_groups[district["city_short"]].append(row)
        bike_update_times.extend(stats["bike_update_times"])

    trend_values = [
        round(statistics.mean(row["trend_values"][i] for row in district_rows), 2)
        for i in range(len(time_axis))
    ]

    city_summary = []
    for city, rows in city_groups.items():
        city_summary.append(
            {
                "city": city,
                "cbmf": round(statistics.mean(row["cbmf"] for row in rows), 2),
                "rain_mm": round(statistics.mean(row["rain_mm"] for row in rows), 2),
                "bike_stress": round(statistics.mean(row["bike_stress"] for row in rows), 3),
                "district_count": len(rows),
                "bike_station_count": sum(row["bike_station_count"] for row in rows),
                "low_bike_station_count": sum(row["low_bike_station_count"] for row in rows),
            }
        )

    overall_cbmf = round(statistics.mean(row["cbmf"] for row in district_rows), 2)
    rank_data = sorted(district_rows, key=lambda row: row["cbmf"], reverse=True)
    data = {
        "metric_name": "雨天通勤崩潰放大係數",
        "cbmf": overall_cbmf,
        "avg_rain": round(statistics.mean(row["rain_mm"] for row in district_rows), 2),
        "avg_bike_stress": round(statistics.mean(row["bike_stress"] for row in district_rows), 3),
        "delay": round((overall_cbmf - 1) * 28),
        "hotspots": len([row for row in district_rows if row["cbmf"] >= 1.55]),
        "district_count": len(district_rows),
        "city_summary": city_summary,
        "rank_data": [
            {
                "name": row["name"],
                "city": row["city"],
                "score": row["cbmf"],
                "rain_mm": row["rain_mm"],
                "bike_stress": row["bike_stress"],
                "delay_min": row["delay_min"],
            }
            for row in rank_data[:10]
        ],
        "districts": district_rows,
        "trend_labels": [label[11:16] for label in time_axis],
        "trend_values": trend_values,
        "time_axis": time_axis,
        "update_time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "data_time": {
            "weather_hour": all_times[current_idx],
            "bike_latest_update": max(bike_update_times) if bike_update_times else None,
        },
        "alignment": {
            "spatial_unit": "雙北 41 行政區",
            "time_unit": "逐時降雨趨勢；YouBike 為同批次即時快照",
            "formula": "CBMF = 1 + 0.62 * min(1.6, rain_mm / 10) + 0.58 * bike_stress",
        },
        "sources": [
            {
                "name": "TDX YouBike Station/Availability - Taipei",
                "url": "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/Taipei",
            },
            {
                "name": "TDX YouBike Station/Availability - NewTaipei",
                "url": "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/NewTaipei",
            },
            {
                "name": "Open-Meteo Forecast API precipitation",
                "url": "https://open-meteo.com/",
            },
            {
                "name": "Taipei City Dashboard metrotaipei_town.geojson",
                "url": "../Taipei-City-Dashboard-FE/public/mapData/metrotaipei_town.geojson",
            },
        ],
        "notes": [
            "主排名只使用臺北市與新北市皆可取得且可對齊到行政區的資料。",
            "道路即時速率目前 TDX Live API 支援臺北市但不接受 NewTaipei，因此未納入主 CBMF 排名。",
        ],
    }
    return data


def main():
    data = build_result()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f"Data saved: CBMF={data['cbmf']} districts={data['district_count']} updated={data['update_time']}")


if __name__ == "__main__":
    main()
