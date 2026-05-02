#!/usr/bin/env python3
"""Build local GeoJSON for the Metro Taipei today-work component."""

import argparse
import csv
import io
import json
import math
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_TAIPEI_FILE = "/Users/user/Downloads/Todaywork.json"
DEFAULT_OUTPUT = (
    "/Users/user/Documents/codefest_2026/"
    "Taipei-City-Dashboard-FE/public/mapData/traffic_todaywork_metrotaipei.geojson"
)
NTPC_ROAD_DIG_CSV_URL = "https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv"
NTPC_PAGE_SIZE = 100

TAIPEI_DISTRICT_NAMES = {
    "北投",
    "士林",
    "內湖",
    "南港",
    "松山",
    "信義",
    "中山",
    "大同",
    "中正",
    "萬華",
    "大安",
    "文山",
}


def twd97_to_lonlat(x, y):
    a = 6378137.0
    b = 6356752.314245
    lng0 = math.radians(121)
    k0 = 0.9999
    dx = 250000
    e = math.sqrt(1 - (b * b) / (a * a))

    x = float(x) - dx
    y = float(y)
    m = y / k0
    mu = m / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    j1 = 3 * e1 / 2 - 27 * e1**3 / 32
    j2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
    j3 = 151 * e1**3 / 96
    j4 = 1097 * e1**4 / 512
    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)

    e2 = e**2 / (1 - e**2)
    c1 = e2 * math.cos(fp) ** 2
    t1 = math.tan(fp) ** 2
    r1 = a * (1 - e**2) / ((1 - e**2 * math.sin(fp) ** 2) ** 1.5)
    n1 = a / math.sqrt(1 - e**2 * math.sin(fp) ** 2)
    d = x / (n1 * k0)

    lat = fp - (n1 * math.tan(fp) / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * e2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * e2 - 3 * c1**2) * d**6 / 720
    )
    lon = lng0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * e2 + 24 * t1**2) * d**5 / 120
    ) / math.cos(fp)

    return [round(math.degrees(lon), 7), round(math.degrees(lat), 7)]


def normalize_district(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value in TAIPEI_DISTRICT_NAMES:
        return f"{value}區"
    return value


def roc_date(value):
    value = str(value or "").strip()
    if len(value) < 7:
        return None
    year = int(value[:-4]) + 1911
    month = int(value[-4:-2])
    day = int(value[-2:])
    return date(year, month, day)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f, strict=False)


def fetch_ntpc_road_dig_rows():
    rows = []
    page = 0
    while True:
        url = f"{NTPC_ROAD_DIG_CSV_URL}?{urlencode({'page': page, 'size': NTPC_PAGE_SIZE})}"
        request = Request(url, headers={"accept": "text/csv;charset=UTF-8", "User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8-sig", errors="replace")
        page_rows = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < NTPC_PAGE_SIZE:
            break
        page += 1
    return rows


def taipei_features(path):
    data = load_json(path)
    features = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        x = props.get("X")
        y = props.get("Y")
        if not x or not y:
            geometry = feature.get("geometry") or {}
            coords = geometry.get("coordinates") or []
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
        if not x or not y:
            continue
        district = normalize_district(props.get("C_Name"))
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": twd97_to_lonlat(x, y)},
                "properties": {
                    "source_city": "臺北市",
                    "source": "data.taipei Todaywork.json",
                    "case_no": props.get("Ac_no"),
                    "project_name": props.get("NPurp"),
                    "organizer": props.get("App_Name"),
                    "district": district,
                    "address": props.get("Addr"),
                    "start_date": props.get("Cb_Da"),
                    "end_date": props.get("Ce_Da"),
                    "date_range": f"{props.get('Cb_Da', '')}~{props.get('Ce_Da', '')}",
                },
            }
        )
    return features


def ntpc_features(today):
    data = fetch_ntpc_road_dig_rows()
    features = []
    for row in data:
        start_date = roc_date(row.get("casestartdate_yyymmddroc"))
        end_date = roc_date(row.get("caseenddate_yyymmddroc"))
        if not start_date or not end_date or not (start_date <= today <= end_date):
            continue
        x = row.get("twd97x")
        y = row.get("twd97y")
        if not x or not y:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": twd97_to_lonlat(x, y)},
                "properties": {
                    "source_city": "新北市",
                    "source": "新北市政府道路挖掘資訊",
                    "case_no": row.get("licno") or row.get("caseid"),
                    "project_name": row.get("constname"),
                    "organizer": row.get("supervise") or row.get("examunit") or row.get("constructionunit"),
                    "district": normalize_district(row.get("district")),
                    "address": row.get("digsite"),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "date_range": f"{row.get('casestartdate_yyymmddroc', '')}~{row.get('caseenddate_yyymmddroc', '')}",
                    "status": row.get("statdesc"),
                },
            }
        )
    return features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--taipei-file", default=DEFAULT_TAIPEI_FILE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    features = taipei_features(args.taipei_file)
    features.extend(ntpc_features(date.today()))
    geojson = {"type": "FeatureCollection", "features": features}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(features)} features to {args.output}")


if __name__ == "__main__":
    main()
