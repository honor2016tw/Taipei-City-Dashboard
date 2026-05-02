from airflow import DAG
import json
import math
import os
import statistics

from operators.common_pipeline import CommonDag


TDX_TOKEN_URL = "https://apiatis.ntpc.gov.tw/ntpc-api/TDX/Token"
TDX_METRO_STATIONS = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC?$format=JSON"
TDX_BIKE_STATION = "https://tdx.transportdata.tw/api/basic/v2/Bike/Station/City/{city}?$format=JSON"
TDX_BIKE_AVAILABILITY = "https://tdx.transportdata.tw/api/basic/v2/Bike/Availability/City/{city}?$format=JSON"
TDX_BUS_STOPS = "https://tdx.transportdata.tw/api/basic/v2/Bus/Stop/City/{city}?$format=JSON"
TDX_BUS_ETA = "https://tdx.transportdata.tw/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city}?$format=JSON"

METHOD_VERSION = "last_mile_service_v1"
STATION_RADIUS_M = 500

LINE_META = {
    "BR": {"name": "文湖線", "color": "#c48c31", "order": 1},
    "R": {"name": "淡水信義線", "color": "#e3002c", "order": 2},
    "G": {"name": "松山新店線", "color": "#008659", "order": 3},
    "O": {"name": "中和新蘆線", "color": "#f8b61c", "order": 4},
    "BL": {"name": "板南線", "color": "#0070bd", "order": 5},
}

ROUTE_SOURCE_FILES = {
    "BR": ["metro_br_line_car_route.geojson"],
    "R": ["metro_r_line_car_route.geojson", "metro_r_line_car_route_2.geojson"],
    "G": ["metro_g_line_car_route.geojson", "metro_g_line_car_route_2.geojson"],
    "O": ["metro_o_line_car_route.geojson", "metro_o_line_car_route_2.geojson"],
    "BL": ["metro_bl_line_car_route.geojson"],
}

WEIGHTS = {
    "bike_pickup": 0.30,
    "bike_return": 0.25,
    "bus": 0.30,
    "coverage": 0.15,
}


def _fetch_json(session, url, headers=None, timeout=60):
    response = session.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _get_tdx_headers(session):
    token_payload = _fetch_json(session, TDX_TOKEN_URL)
    token = token_payload.get("token") or token_payload.get("access_token")
    if not token:
        raise RuntimeError("TDX token response does not include a bearer token.")
    return {"Authorization": f"Bearer {token}", "User-Agent": "metro-last-mile/1.0"}


def _city_short(value):
    if value in ("臺北市", "台北市", "Taipei", "TPE"):
        return "臺北"
    if value in ("新北市", "NewTaipei", "NWT"):
        return "新北"
    return value or "未知"


def _normalize_line_id(value):
    value = str(value or "").upper()
    if value.startswith("BL"):
        return "BL"
    if value.startswith("BR"):
        return "BR"
    if value.startswith("R"):
        return "R"
    if value.startswith("G"):
        return "G"
    if value.startswith("O"):
        return "O"
    return ""


def _haversine_m(lon1, lat1, lon2, lat2):
    radius = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearby(items, unit, radius_m=STATION_RADIUS_M):
    lat_delta = radius_m / 111320
    lon_delta = radius_m / (111320 * max(0.2, math.cos(math.radians(unit["lat"]))))
    return [
        item
        for item in items
        if item["city"] == unit["city"]
        and abs(item["lat"] - unit["lat"]) <= lat_delta
        and abs(item["lon"] - unit["lon"]) <= lon_delta
        and _haversine_m(unit["lon"], unit["lat"], item["lon"], item["lat"]) <= radius_m
    ]


def _fetch_metro_stations(session, headers):
    rows = _fetch_json(session, TDX_METRO_STATIONS, headers=headers)
    seen = {}
    for row in rows:
        pos = row.get("StationPosition") or {}
        name = row.get("StationName", {}).get("Zh_tw")
        lon = pos.get("PositionLon")
        lat = pos.get("PositionLat")
        if not name or lon is None or lat is None:
            continue

        city = _city_short(row.get("LocationCity") or row.get("LocationCityCode"))
        if city not in ("臺北", "新北"):
            continue

        line_id = _normalize_line_id(row.get("StationID", ""))
        if line_id not in LINE_META:
            continue

        if name not in seen:
            seen[name] = {
                "station_id": f"TRTC-{name}",
                "station_name": name,
                "city": city,
                "town": row.get("LocationTown") or "",
                "lon_values": [],
                "lat_values": [],
                "line_ids": [],
            }
        seen[name]["lon_values"].append(float(lon))
        seen[name]["lat_values"].append(float(lat))
        seen[name]["line_ids"].append(line_id)

    stations = []
    for station in seen.values():
        line_ids = sorted(
            set(station.pop("line_ids")),
            key=lambda line_id: LINE_META[line_id]["order"],
        )
        station["lon"] = statistics.mean(station.pop("lon_values"))
        station["lat"] = statistics.mean(station.pop("lat_values"))
        station["line_ids"] = line_ids
        station["network_degree"] = len(line_ids)
        stations.append(station)
    return stations


def _fetch_bike_city(session, city, headers):
    stations = _fetch_json(session, TDX_BIKE_STATION.format(city=city), headers=headers)
    availability = _fetch_json(session, TDX_BIKE_AVAILABILITY.format(city=city), headers=headers)
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
                "city": _city_short(city),
                "lon": float(pos["PositionLon"]),
                "lat": float(pos["PositionLat"]),
                "capacity": int(station.get("BikesCapacity") or 0),
                "rent": int(live.get("AvailableRentBikes") or 0),
                "return": int(live.get("AvailableReturnBikes") or 0),
                "service": int(live.get("ServiceStatus") or 0),
            }
        )
    return rows


def _fetch_bus_city(session, city, headers):
    stops = _fetch_json(session, TDX_BUS_STOPS.format(city=city), headers=headers)
    eta = _fetch_json(session, TDX_BUS_ETA.format(city=city), headers=headers)
    stop_by_uid = {}
    for stop in stops:
        pos = stop.get("StopPosition") or {}
        if pos.get("PositionLon") is None or pos.get("PositionLat") is None:
            continue
        stop_by_uid[stop["StopUID"]] = {
            "uid": stop["StopUID"],
            "name": stop.get("StopName", {}).get("Zh_tw", stop["StopUID"]),
            "city": _city_short(stop.get("LocationCityCode") or city),
            "lon": float(pos["PositionLon"]),
            "lat": float(pos["PositionLat"]),
            "eta_seconds": [],
            "status_total": 0,
            "status_bad": 0,
        }
    for item in eta:
        stop = stop_by_uid.get(item.get("StopUID"))
        if not stop:
            continue
        stop["status_total"] += 1
        if item.get("StopStatus") != 0:
            stop["status_bad"] += 1
        estimate = item.get("EstimateTime")
        if isinstance(estimate, (int, float)) and 0 <= estimate <= 3600:
            stop["eta_seconds"].append(float(estimate))
    return list(stop_by_uid.values())


def _bike_scores(stations):
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


def _bus_scores(stops):
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


def _coverage_score(bike_count, bus_count):
    bike_part = min(1, bike_count / 6)
    bus_part = min(1, bus_count / 35)
    return round(0.45 * bike_part + 0.55 * bus_part, 3)


def _service_status(score):
    if score >= 80:
        return "good", "穩定"
    if score >= 65:
        return "watch", "需觀察"
    if score >= 50:
        return "weak", "偏弱"
    return "failing", "風險高"


def _station_type(unit, bike_count, bus_count):
    if unit["network_degree"] >= 2:
        return "轉乘型站"
    if bus_count >= 45 and bike_count >= 4:
        return "通勤型站"
    if bike_count >= 8:
        return "商圈混合型站"
    if bus_count <= 12 and bike_count <= 2:
        return "郊區型站"
    return "一般接駁型站"


def _build_rows(data_time):
    import requests

    session = requests.Session()
    headers = _get_tdx_headers(session)
    metro_stations = _fetch_metro_stations(session, headers)
    bike_stations = _fetch_bike_city(session, "Taipei", headers) + _fetch_bike_city(session, "NewTaipei", headers)
    bus_stops = _fetch_bus_city(session, "Taipei", headers) + _fetch_bus_city(session, "NewTaipei", headers)

    rows = []
    for unit in metro_stations:
        bikes_nearby = _nearby(bike_stations, unit)
        stops_nearby = _nearby(bus_stops, unit)
        bike = _bike_scores(bikes_nearby)
        bus = _bus_scores(stops_nearby)
        coverage = _coverage_score(bike["bike_station_count"], bus["bus_stop_count"])
        components = {
            "bike_pickup": bike["pickup_score"],
            "bike_return": bike["return_score"],
            "bus": bus["bus_score"],
            "coverage": coverage,
        }
        service_score = round(sum(components[key] * WEIGHTS[key] for key in components) * 100, 1)
        risk_score = round(100 - service_score, 1)
        service_status, status_label = _service_status(service_score)
        station_type = _station_type(unit, bike["bike_station_count"], bus["bus_stop_count"])

        for line_id in unit["line_ids"]:
            line_meta = LINE_META[line_id]
            rows.append(
                {
                    "data_time": data_time,
                    "method_version": METHOD_VERSION,
                    "station_id": unit["station_id"],
                    "station_name": unit["station_name"],
                    "city": unit["city"],
                    "town": unit["town"],
                    "lon": round(unit["lon"], 6),
                    "lat": round(unit["lat"], 6),
                    "line_id": line_id,
                    "line_name": line_meta["name"],
                    "line_color": line_meta["color"],
                    "network_degree": unit["network_degree"],
                    "station_type": station_type,
                    "service_score": service_score,
                    "risk_score": risk_score,
                    "service_status": service_status,
                    "status_label": status_label,
                    "pickup_score": components["bike_pickup"],
                    "return_score": components["bike_return"],
                    "bus_score": components["bus"],
                    "coverage_score": components["coverage"],
                    "bike_station_count": bike["bike_station_count"],
                    "available_rent_bikes": bike["available_rent_bikes"],
                    "available_return_bikes": bike["available_return_bikes"],
                    "bike_offline_rate": bike["bike_offline_rate"],
                    "bus_stop_count": bus["bus_stop_count"],
                    "bus_eta_sample_count": bus["bus_eta_sample_count"],
                    "median_eta_min": bus["median_eta_min"],
                    "bus_issue_rate": bus["bus_issue_rate"],
                }
            )
    return rows


def _station_feature(row):
    return {
        "type": "Feature",
        "properties": {
            "data_time": row["data_time"],
            "station_id": row["station_id"],
            "station_name": row["station_name"],
            "city": row["city"],
            "town": row["town"],
            "line_id": row["line_id"],
            "line_name": row["line_name"],
            "service_score": row["service_score"],
            "risk_score": row["risk_score"],
            "service_status": row["service_status"],
            "status_label": row["status_label"],
            "station_type": row["station_type"],
            "bike_station_count": row["bike_station_count"],
            "available_rent_bikes": row["available_rent_bikes"],
            "available_return_bikes": row["available_return_bikes"],
            "median_eta_min": row["median_eta_min"],
        },
        "geometry": {
            "type": "Point",
            "coordinates": [row["lon"], row["lat"]],
        },
    }


def _export_station_geojson(rows, output_dir):
    for line_id in LINE_META:
        line_rows = [row for row in rows if row["line_id"] == line_id]
        output = {
            "type": "FeatureCollection",
            "name": f"metro_last_mile_{line_id.lower()}_stations",
            "features": [_station_feature(row) for row in line_rows],
        }
        path = os.path.join(output_dir, f"metro_last_mile_{line_id.lower()}_stations.geojson")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False)


def _export_route_geojson(data_time, output_dir):
    for line_id, filenames in ROUTE_SOURCE_FILES.items():
        features = []
        for filename in filenames:
            source_path = os.path.join(output_dir, filename)
            if not os.path.exists(source_path):
                continue
            with open(source_path, "r", encoding="utf-8") as file:
                geojson = json.load(file)
            for feature in geojson.get("features", []):
                feature = dict(feature)
                feature["properties"] = {
                    **feature.get("properties", {}),
                    "data_time": data_time,
                    "line_id": line_id,
                    "line_name": LINE_META[line_id]["name"],
                    "line_color": LINE_META[line_id]["color"],
                }
                features.append(feature)
        if not features:
            continue
        output = {
            "type": "FeatureCollection",
            "name": f"metro_last_mile_{line_id.lower()}_route",
            "features": features,
        }
        path = os.path.join(output_dir, f"metro_last_mile_{line_id.lower()}_route.geojson")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False)


def _export_mapdata(rows, data_time):
    output_dir = os.environ.get("DASHBOARD_FE_MAPDATA_DIR", "/opt/Taipei-City-Dashboard-FE/public/mapData")
    if not output_dir or not os.path.isdir(output_dir):
        print(f"Skip mapData export, directory does not exist: {output_dir}")
        return
    _export_station_geojson(rows, output_dir)
    _export_route_geojson(data_time, output_dir)
    print(f"Exported metro last-mile GeoJSON files to {output_dir}")


def _metro_last_mile_service_health(**kwargs):
    import pandas as pd
    from sqlalchemy import create_engine
    from utils.get_time import get_tpe_now_time_str
    from utils.load_stage import (
        save_dataframe_to_postgresql,
        update_lasttime_in_data_to_dataset_info,
    )

    ready_data_db_uri = kwargs.get("ready_data_db_uri")
    dag_infos = kwargs.get("dag_infos")
    dag_id = dag_infos.get("dag_id")
    load_behavior = dag_infos.get("load_behavior")
    default_table = dag_infos.get("ready_data_default_table")
    history_table = dag_infos.get("ready_data_history_table")
    data_time = get_tpe_now_time_str(is_with_tz=True)

    rows = _build_rows(data_time)
    if not rows:
        raise ValueError("No metro last-mile service rows were generated.")

    ready_data = pd.DataFrame(rows)
    ready_data["data_time"] = pd.to_datetime(ready_data["data_time"], errors="coerce")

    engine = create_engine(ready_data_db_uri)
    save_dataframe_to_postgresql(
        engine,
        data=ready_data,
        load_behavior=load_behavior,
        default_table=default_table,
        history_table=history_table,
    )
    update_lasttime_in_data_to_dataset_info(engine, dag_id, data_time)
    _export_mapdata(rows, data_time)


dag = CommonDag(
    proj_folder="proj_city_dashboard",
    dag_folder="metro_last_mile_service_health",
)
dag.create_dag(etl_func=_metro_last_mile_service_health)

