#!/usr/bin/env python3
"""Run the Metro Taipei today-work import once without Airflow."""

import argparse
import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


TAIPEI_TODAYWORK_URL = "https://tpnco.blob.core.windows.net/blobfs/Todaywork.json"
NTPC_ROAD_DIG_CSV_URL = "https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv"
NTPC_PAGE_SIZE = 100
DEFAULT_TAIPEI_FILE = "/Users/user/Downloads/Todaywork.json"

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

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS public.traffic_todayworks_metrotaipei (
    data_time timestamp with time zone,
    source_city text,
    source text,
    case_no text,
    organizer text,
    project_name text,
    district text,
    address text,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    date_range text,
    is_expired boolean,
    xy_key text,
    _ctime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    _mtime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ogc_fid serial PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS public.traffic_todayworks_metrotaipei_history (
    data_time timestamp with time zone,
    source_city text,
    source text,
    case_no text,
    organizer text,
    project_name text,
    district text,
    address text,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    date_range text,
    is_expired boolean,
    xy_key text,
    _ctime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    _mtime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ogc_fid serial PRIMARY KEY
);

CREATE INDEX IF NOT EXISTS traffic_todayworks_metrotaipei_district_idx
ON public.traffic_todayworks_metrotaipei (district);

CREATE INDEX IF NOT EXISTS traffic_todayworks_metrotaipei_history_data_time_idx
ON public.traffic_todayworks_metrotaipei_history (data_time);
"""

COLUMNS = [
    "data_time",
    "source_city",
    "source",
    "case_no",
    "organizer",
    "project_name",
    "district",
    "address",
    "start_date",
    "end_date",
    "date_range",
    "is_expired",
    "xy_key",
]


def tpe_now():
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def request_text(url, params=None, timeout=60):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "accept": "text/csv;charset=UTF-8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def normalize_district_name(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value in TAIPEI_DISTRICT_NAMES:
        return f"{value}區"
    return value


def to_ad_date(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    date_part = value.split(" ")[0].replace("/", "-")
    parts = date_part.split("-")
    if len(parts) != 3:
        return None
    year = int(parts[0])
    if year < 1911:
        year += 1911
    return f"{year:04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"


def roc_compact_to_ad_date(value):
    value = str(value or "").strip()
    if len(value) < 7:
        return None
    try:
        year = int(value[:-4]) + 1911
        month = int(value[-4:-2])
        day = int(value[-2:])
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def load_taipei_json(path):
    if path:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f, strict=False)
    return json.loads(request_text(TAIPEI_TODAYWORK_URL).lstrip("\ufeff"))


def fetch_ntpc_road_dig_rows():
    rows = []
    page = 0
    while True:
        text = request_text(
            NTPC_ROAD_DIG_CSV_URL,
            params={"page": page, "size": NTPC_PAGE_SIZE},
        )
        page_rows = list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < NTPC_PAGE_SIZE:
            break
        page += 1
    return rows


def build_rows(taipei_file=None, skip_ntpc=False):
    data_time = tpe_now().isoformat()
    today = tpe_now().date()
    taipei_raw = load_taipei_json(taipei_file)

    rows = []
    for feature in taipei_raw.get("features", []):
        props = feature.get("properties", {})
        rows.append(
            {
                "data_time": data_time,
                "source_city": "臺北市",
                "source": "data.taipei Todaywork.json",
                "case_no": props.get("Ac_no"),
                "organizer": props.get("App_Name"),
                "project_name": props.get("NPurp"),
                "district": normalize_district_name(props.get("C_Name")),
                "address": props.get("Addr"),
                "start_date": to_ad_date(props.get("Cb_Da")),
                "end_date": to_ad_date(props.get("Ce_Da")),
                "date_range": f"{props.get('Cb_Da', '')}~{props.get('Ce_Da', '')}",
                "is_expired": None,
                "xy_key": None,
            }
        )

    if skip_ntpc:
        return rows

    for row in fetch_ntpc_road_dig_rows():
        start_date = roc_compact_to_ad_date(row.get("casestartdate_yyymmddroc"))
        end_date = roc_compact_to_ad_date(row.get("caseenddate_yyymmddroc"))
        if not start_date or not end_date:
            continue
        if not (datetime.fromisoformat(start_date).date() <= today <= datetime.fromisoformat(end_date).date()):
            continue
        rows.append(
            {
                "data_time": data_time,
                "source_city": "新北市",
                "source": "新北市政府道路挖掘資訊 API",
                "case_no": row.get("licno") or row.get("caseid"),
                "organizer": row.get("supervise") or row.get("examunit") or row.get("constructionunit"),
                "project_name": row.get("constname"),
                "district": normalize_district_name(row.get("district")),
                "address": row.get("digsite"),
                "start_date": start_date,
                "end_date": end_date,
                "date_range": f"{row.get('casestartdate_yyymmddroc', '')}~{row.get('caseenddate_yyymmddroc', '')}",
                "is_expired": False,
                "xy_key": ",".join(value for value in [row.get("twd97x"), row.get("twd97y")] if value) or None,
            }
        )
    return rows


def dedupe_rows(rows):
    output = []
    seen = set()
    for row in rows:
        key = (row["source_city"], row["case_no"], row["district"], row["address"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return "'" + str(value).replace("'", "''") + "'"


def build_insert_sql(table_name, rows):
    if not rows:
        return ""
    column_sql = ", ".join(COLUMNS)
    values_sql = ",\n".join(
        "(" + ", ".join(sql_literal(row.get(column)) for column in COLUMNS) + ")"
        for row in rows
    )
    return f"INSERT INTO public.{table_name} ({column_sql}) VALUES\n{values_sql};"


def print_sql(rows, create_only=False):
    print(CREATE_TABLES_SQL)
    if create_only:
        return
    print("TRUNCATE TABLE public.traffic_todayworks_metrotaipei;")
    print(build_insert_sql("traffic_todayworks_metrotaipei", rows))
    print(build_insert_sql("traffic_todayworks_metrotaipei_history", rows))


def connect(database_url):
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError("psycopg2 is required. Use --sql-only if it is not installed.") from exc
    return psycopg2.connect(database_url)


def ensure_tables(conn):
    with conn.cursor() as cursor:
        cursor.execute(CREATE_TABLES_SQL)
    conn.commit()


def insert_rows(conn, rows):
    from psycopg2.extras import execute_values

    values = [tuple(row.get(column) for column in COLUMNS) for row in rows]
    column_sql = ", ".join(COLUMNS)
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE public.traffic_todayworks_metrotaipei;")
        execute_values(
            cursor,
            f"INSERT INTO public.traffic_todayworks_metrotaipei ({column_sql}) VALUES %s",
            values,
            page_size=1000,
        )
        execute_values(
            cursor,
            f"INSERT INTO public.traffic_todayworks_metrotaipei_history ({column_sql}) VALUES %s",
            values,
            page_size=1000,
        )
    conn.commit()


def parse_args():
    parser = argparse.ArgumentParser(description="Import traffic_todaywork_metrotaipei once without Airflow.")
    parser.add_argument("--database-url", default=os.getenv("DASHBOARD_DATABASE_URL") or os.getenv("DATABASE_URL"))
    parser.add_argument("--taipei-file", default=DEFAULT_TAIPEI_FILE if os.path.exists(DEFAULT_TAIPEI_FILE) else None)
    parser.add_argument("--skip-ntpc", action="store_true", help="Only import Taipei data.")
    parser.add_argument("--create-only", action="store_true", help="Only create tables and indexes.")
    parser.add_argument("--sql-only", action="store_true", help="Print SQL instead of connecting with psycopg2.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.sql_only:
        rows = [] if args.create_only else dedupe_rows(build_rows(args.taipei_file, args.skip_ntpc))
        print_sql(rows, args.create_only)
        return

    if not args.database_url:
        raise SystemExit("Missing --database-url or DASHBOARD_DATABASE_URL.")

    conn = connect(args.database_url)
    try:
        ensure_tables(conn)
        if args.create_only:
            print("Tables and indexes are ready.")
            return
        rows = dedupe_rows(build_rows(args.taipei_file, args.skip_ntpc))
        insert_rows(conn, rows)
        print(f"Inserted {len(rows)} current rows and appended {len(rows)} history rows.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
