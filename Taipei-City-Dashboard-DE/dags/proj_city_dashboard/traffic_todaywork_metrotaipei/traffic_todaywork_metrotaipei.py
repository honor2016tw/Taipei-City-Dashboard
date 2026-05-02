from airflow import DAG
from html.parser import HTMLParser
import re

from operators.common_pipeline import CommonDag


TAIPEI_TODAYWORK_URL = "https://tpnco.blob.core.windows.net/blobfs/Todaywork.json"
NTPC_ROAD_CONST_URL = "https://roadmt.maintenance.ntpc.gov.tw/iROAD/Home/GetCaseRoadConst"

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


class RoadConstTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_body_row = False
        self._in_cell = False
        self._cells = []
        self._cell_parts = []
        self._xy_key = None
        self._is_expired = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr" and "divTableBody" in attrs.get("class", ""):
            self._in_body_row = True
            self._cells = []
            self._xy_key = None
            self._is_expired = None
            onclick = attrs.get("onclick", "")
            match = re.search(r"GetXY\('([^']+)'\s*,\s*'([^']+)'\)", onclick)
            if match:
                self._xy_key = match.group(1)
                self._is_expired = match.group(2) == "Y"
        elif self._in_body_row and tag == "td":
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data):
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag):
        if self._in_body_row and tag == "td":
            value = " ".join("".join(self._cell_parts).split())
            self._cells.append(value)
            self._in_cell = False
        elif self._in_body_row and tag == "tr":
            if len(self._cells) >= 6:
                self.rows.append(
                    {
                        "case_no": self._cells[0],
                        "organizer": self._cells[1],
                        "project_name": self._cells[2],
                        "district": self._cells[3],
                        "address": self._cells[4],
                        "date_range": self._cells[5],
                        "xy_key": self._xy_key,
                        "is_expired": self._is_expired,
                    }
                )
            self._in_body_row = False


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


def _split_date_range(value):
    if not value:
        return None, None
    parts = str(value).replace("～", "~").split("~", 1)
    start_date = _to_ad_date(parts[0])
    end_date = _to_ad_date(parts[1]) if len(parts) > 1 else None
    return start_date, end_date


def _parse_ntpc_rows(html):
    parser = RoadConstTableParser()
    parser.feed(html)
    return parser.rows


def _parse_total_pages(html):
    match = re.search(r"共\s*(\d+)\s*頁", html)
    return int(match.group(1)) if match else 1


def _parse_current_page(html):
    match = re.search(r"當前第\s*(\d+)\s*頁", html)
    return int(match.group(1)) if match else None


def _request_ntpc(session, method="get", params=None, data=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html, */*; q=0.01",
        "Referer": "https://roadmt.maintenance.ntpc.gov.tw/iROAD/",
        "X-Requested-With": "XMLHttpRequest",
    }
    if method == "post":
        response = session.post(
            NTPC_ROAD_CONST_URL,
            data=data,
            headers=headers,
            timeout=60,
            verify=True,
        )
    else:
        response = session.get(
            NTPC_ROAD_CONST_URL,
            params=params,
            headers=headers,
            timeout=60,
            verify=True,
        )
    response.raise_for_status()
    return response.text


def _ntpc_page_candidates(page):
    page = str(page)
    return [
        ("post", None, {"page": page, "gridId": "gv_dig5"}),
        ("post", None, {"page": page, "gv": "gv_dig5"}),
        ("post", None, {"nowPage": page, "gv": "gv_dig5"}),
        ("post", None, {"pageIndex": page, "gridViewID": "gv_dig5"}),
        ("post", None, {"txt_page_gv_dig5": page}),
        ("get", {"page": page}, None),
        ("get", {"Page": page}, None),
        ("get", {"nowPage": page}, None),
        ("get", {"pageIndex": page}, None),
    ]


def _fetch_ntpc_all_pages():
    import requests

    session = requests.Session()
    first_html = _request_ntpc(session)
    first_rows = _parse_ntpc_rows(first_html)
    if not first_rows:
        raise ValueError("No New Taipei iROAD road construction rows were parsed.")

    rows = first_rows
    seen_case_no = {row["case_no"] for row in rows}
    total_pages = _parse_total_pages(first_html)
    selected_strategy = None

    for page in range(2, total_pages + 1):
        page_html = None
        if selected_strategy:
            method, params_template, data_template = selected_strategy
            params = {
                key: (str(page) if value == "{page}" else value)
                for key, value in (params_template or {}).items()
            }
            data = {
                key: (str(page) if value == "{page}" else value)
                for key, value in (data_template or {}).items()
            }
            page_html = _request_ntpc(session, method, params=params, data=data)
        else:
            for method, params, data in _ntpc_page_candidates(page):
                page_html = _request_ntpc(session, method, params=params, data=data)
                candidate_rows = _parse_ntpc_rows(page_html)
                candidate_cases = {row["case_no"] for row in candidate_rows}
                current_page = _parse_current_page(page_html)
                if candidate_rows and (
                    current_page == page or not candidate_cases.issubset(seen_case_no)
                ):
                    selected_strategy = (
                        method,
                        {
                            key: ("{page}" if value == str(page) else value)
                            for key, value in (params or {}).items()
                        },
                        {
                            key: ("{page}" if value == str(page) else value)
                            for key, value in (data or {}).items()
                        },
                    )
                    break

        page_rows = _parse_ntpc_rows(page_html or "")
        new_rows = [row for row in page_rows if row["case_no"] not in seen_case_no]
        if not new_rows:
            break
        seen_case_no.update(row["case_no"] for row in new_rows)
        rows.extend(new_rows)

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

    ntpc_rows = []
    for row in _fetch_ntpc_all_pages():
        start_date, end_date = _split_date_range(row.get("date_range"))
        ntpc_rows.append(
            {
                "data_time": data_time,
                "source_city": "新北市",
                "source": "iROAD GetCaseRoadConst",
                "case_no": row.get("case_no"),
                "organizer": row.get("organizer"),
                "project_name": row.get("project_name"),
                "district": _normalize_district_name(row.get("district")),
                "address": row.get("address"),
                "start_date": start_date,
                "end_date": end_date,
                "date_range": row.get("date_range"),
                "is_expired": row.get("is_expired"),
                "xy_key": row.get("xy_key"),
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
