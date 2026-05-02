#!/usr/bin/env python3
"""Export stationMetrics to a GeoJSON file for Mapbox map layers."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    data_path = Path(__file__).parent / "output" / "dashboard_data.json"
    out_path = (
        Path(__file__).resolve().parent.parent
        / "Taipei-City-Dashboard-FE"
        / "public"
        / "mapData"
        / "youbike_peak_pressure_stations.geojson"
    )

    print(f"Reading {data_path} …")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    metrics = data["stationMetrics"]

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [m["lon"], m["lat"]],
            },
            "properties": {
                "station_id":    m["station_id"],
                "name":          m["name"],
                "area":          m["area"],
                "city":          m["city"],
                "segment":       m["segment"],
                "role":          m["role"],
                "avg_bike_rate": round(m["avg_bike_rate"], 4),
                "avg_dock_rate": round(m["avg_dock_rate"], 4),
                "zero_bike_rate": round(m["zero_bike_rate"], 4),
            },
        }
        for m in metrics
    ]

    geojson = {"type": "FeatureCollection", "features": features}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"Written {len(features)} features → {out_path}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
