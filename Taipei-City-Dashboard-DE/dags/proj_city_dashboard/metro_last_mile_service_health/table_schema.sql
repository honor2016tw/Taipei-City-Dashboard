-- Run this in the dashboard database before enabling the DAG.
-- This table stores one row per metro station and metro line, so transfer
-- stations can participate in each related line's dashboard/map layer.

CREATE TABLE IF NOT EXISTS public.metro_last_mile_service_health (
    data_time timestamp with time zone,
    method_version text,
    station_id text,
    station_name text,
    city text,
    town text,
    lon double precision,
    lat double precision,
    line_id text,
    line_name text,
    line_color text,
    network_degree integer,
    station_type text,
    service_score double precision,
    risk_score double precision,
    service_status text,
    status_label text,
    pickup_score double precision,
    return_score double precision,
    bus_score double precision,
    coverage_score double precision,
    bike_station_count integer,
    available_rent_bikes integer,
    available_return_bikes integer,
    bike_offline_rate double precision,
    bus_stop_count integer,
    bus_eta_sample_count integer,
    median_eta_min double precision,
    bus_issue_rate double precision,
    _ctime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    _mtime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ogc_fid serial PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS public.metro_last_mile_service_health_history (
    data_time timestamp with time zone,
    method_version text,
    station_id text,
    station_name text,
    city text,
    town text,
    lon double precision,
    lat double precision,
    line_id text,
    line_name text,
    line_color text,
    network_degree integer,
    station_type text,
    service_score double precision,
    risk_score double precision,
    service_status text,
    status_label text,
    pickup_score double precision,
    return_score double precision,
    bus_score double precision,
    coverage_score double precision,
    bike_station_count integer,
    available_rent_bikes integer,
    available_return_bikes integer,
    bike_offline_rate double precision,
    bus_stop_count integer,
    bus_eta_sample_count integer,
    median_eta_min double precision,
    bus_issue_rate double precision,
    _ctime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    _mtime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ogc_fid serial PRIMARY KEY
);

CREATE INDEX IF NOT EXISTS metro_last_mile_service_health_data_time_idx
ON public.metro_last_mile_service_health (data_time);

CREATE INDEX IF NOT EXISTS metro_last_mile_service_health_line_idx
ON public.metro_last_mile_service_health (line_id);

CREATE INDEX IF NOT EXISTS metro_last_mile_service_health_status_idx
ON public.metro_last_mile_service_health (service_status);

CREATE INDEX IF NOT EXISTS metro_last_mile_service_health_station_idx
ON public.metro_last_mile_service_health (station_name);

CREATE INDEX IF NOT EXISTS metro_last_mile_service_health_history_data_time_idx
ON public.metro_last_mile_service_health_history (data_time);

