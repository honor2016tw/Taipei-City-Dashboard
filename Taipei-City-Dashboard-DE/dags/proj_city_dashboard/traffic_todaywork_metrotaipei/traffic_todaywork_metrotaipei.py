from airflow import DAG
from datetime import datetime, timedelta, timezone
import csv
import io

from operators.common_pipeline import CommonDag


TAIPEI_TODAYWORK_URL = "https://tpnco.blob.core.windows.net/blobfs/Todaywork.json"
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


def _normalize_district_name(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value in TAIPEI_DISTRICT_NAMES:
        return f"{value}區"
    return value


def _to_ad_date(value):
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
    month = int(parts[1])
    day = int(parts[2])
    return f"{year:04d}-{month:02d}-{day:02d}"


def _roc_compact_to_ad_date(value):
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


def _fetch_ntpc_road_dig_rows():
    import requests

    rows = []
    page = 0
    while True:
        response = requests.get(
            NTPC_ROAD_DIG_CSV_URL,
            params={"page": page, "size": NTPC_PAGE_SIZE},
            headers={"accept": "text/csv;charset=UTF-8"},
            timeout=60,
        )
        response.raise_for_status()
        page_rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < NTPC_PAGE_SIZE:
            break
        page += 1

    return rows


def _traffic_todaywork_metrotaipei(**kwargs):
    import json

    import pandas as pd
    from sqlalchemy import create_engine
    from utils.extract_stage import download_file
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

    local_file = download_file("Todaywork.json", TAIPEI_TODAYWORK_URL, is_proxy=False)
    with open(local_file, "r", encoding="utf-8-sig") as f:
        taipei_raw = json.load(f, strict=False)

    taipei_rows = []
    for feature in taipei_raw.get("features", []):
        props = feature.get("properties", {})
        taipei_rows.append(
            {
                "data_time": data_time,
                "source_city": "臺北市",
                "source": "data.taipei Todaywork.json",
                "case_no": props.get("Ac_no"),
                "organizer": props.get("App_Name"),
                "project_name": props.get("NPurp"),
                "district": _normalize_district_name(props.get("C_Name")),
                "address": props.get("Addr"),
                "start_date": _to_ad_date(props.get("Cb_Da")),
                "end_date": _to_ad_date(props.get("Ce_Da")),
                "date_range": f"{props.get('Cb_Da', '')}~{props.get('Ce_Da', '')}",
                "is_expired": None,
                "xy_key": None,
            }
        )

    today = datetime.now(timezone(timedelta(hours=8))).date()
    ntpc_rows = []
    for row in _fetch_ntpc_road_dig_rows():
        start_date = _roc_compact_to_ad_date(row.get("casestartdate_yyymmddroc"))
        end_date = _roc_compact_to_ad_date(row.get("caseenddate_yyymmddroc"))
        if not start_date or not end_date:
            continue
        if not (datetime.fromisoformat(start_date).date() <= today <= datetime.fromisoformat(end_date).date()):
            continue
        ntpc_rows.append(
            {
                "data_time": data_time,
                "source_city": "新北市",
                "source": "新北市政府道路挖掘資訊 API",
                "case_no": row.get("licno") or row.get("caseid"),
                "organizer": row.get("supervise") or row.get("examunit") or row.get("constructionunit"),
                "project_name": row.get("constname"),
                "district": _normalize_district_name(row.get("district")),
                "address": row.get("digsite"),
                "start_date": start_date,
                "end_date": end_date,
                "date_range": f"{row.get('casestartdate_yyymmddroc', '')}~{row.get('caseenddate_yyymmddroc', '')}",
                "is_expired": False,
                "xy_key": ",".join(
                    value
                    for value in [row.get("twd97x"), row.get("twd97y")]
                    if value
                ) or None,
            }
        )

    ready_data = pd.DataFrame(taipei_rows + ntpc_rows)
    ready_data["start_date"] = pd.to_datetime(ready_data["start_date"], errors="coerce")
    ready_data["end_date"] = pd.to_datetime(ready_data["end_date"], errors="coerce")
    ready_data["data_time"] = pd.to_datetime(ready_data["data_time"], errors="coerce")
    ready_data = ready_data.drop_duplicates(
        subset=["source_city", "case_no", "district", "address"],
        keep="first",
    )

    engine = create_engine(ready_data_db_uri)
    save_dataframe_to_postgresql(
        engine,
        data=ready_data,
        load_behavior=load_behavior,
        default_table=default_table,
        history_table=history_table,
    )
    update_lasttime_in_data_to_dataset_info(engine, dag_id, data_time)


dag = CommonDag(proj_folder="proj_city_dashboard", dag_folder="traffic_todaywork_metrotaipei")
dag.create_dag(etl_func=_traffic_todaywork_metrotaipei)
