#!/usr/bin/env python3
"""Load stationMetrics from dashboard_data.json into the dashboard PostgreSQL DB."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    return env


def get_db_params() -> dict[str, str]:
    env_file = Path(__file__).resolve().parent.parent / "docker" / ".env"
    file_env = load_env_file(env_file)

    def get(env_key: str, file_key: str, default: str = "") -> str:
        return os.environ.get(env_key) or file_env.get(file_key) or default

    return {
        "host":     get("POSTGRES_DATA_HOST",     "DB_DASHBOARD_HOST",   "localhost"),
        "port":     get("POSTGRES_DATA_PORT",     "DB_DASHBOARD_PORT",   "5432"),
        "dbname":   get("POSTGRES_DATA_DBNAME",   "DB_DASHBOARD_DBNAME", "dashboard"),
        "user":     get("POSTGRES_DATA_USER",     "DB_DASHBOARD_USER",   "postgres"),
        "password": get("POSTGRES_DATA_PASSWORD", "DB_DASHBOARD_PASSWORD", ""),
    }


def main() -> None:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("psycopg2 not found — install it with: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    data_path = Path(__file__).parent / "output" / "dashboard_data.json"
    print(f"Reading {data_path} …")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    metrics = data["stationMetrics"]
    generated_at = data["generatedAt"]
    print(f"  {len(metrics)} station-segment records, generatedAt={generated_at}")

    params = get_db_params()
    print(f"Connecting to {params['host']}:{params['port']}/{params['dbname']} …")

    conn = psycopg2.connect(**params)
    cur = conn.cursor()

    cur.execute("TRUNCATE TABLE public.youbike_peak_station_metrics RESTART IDENTITY")

    rows = [
        (
            m["station_id"],
            m["name"],
            m["city"],
            m["area"],
            m["address"],
            m["capacity"],
            m["lat"],
            m["lon"],
            m["segment"],
            m["role"],
            m["sample_count"],
            m["date_count"],
            m["avg_bike_rate"],
            m["avg_dock_rate"],
            m["has_bike_rate"],
            m["has_dock_rate"],
            m["zero_bike_rate"],
            m["zero_dock_rate"],
            m["avg_available_bikes"],
            m["avg_available_docks"],
            m["imbalance_rate"],
            m["imbalance_abs"],
            generated_at,
        )
        for m in metrics
    ]

    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO public.youbike_peak_station_metrics (
            station_id, station_name, city, area, address, capacity,
            lat, lon, segment, role, sample_count, date_count,
            avg_bike_rate, avg_dock_rate, has_bike_rate, has_dock_rate,
            zero_bike_rate, zero_dock_rate, avg_available_bikes, avg_available_docks,
            imbalance_rate, imbalance_abs, generated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
        """,
        rows,
        page_size=500,
    )

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM public.youbike_peak_station_metrics")
    count = cur.fetchone()[0]
    print(f"Loaded {count} rows into youbike_peak_station_metrics.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
