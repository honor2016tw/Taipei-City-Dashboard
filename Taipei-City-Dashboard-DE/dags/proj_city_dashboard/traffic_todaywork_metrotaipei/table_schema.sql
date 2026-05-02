-- Run this in the dashboard database before enabling the DAG.

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
