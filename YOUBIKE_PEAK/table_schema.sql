-- Run against the dashboard (postgres-data) database.
-- Creates the youbike_peak_station_metrics table that stores station-level
-- peak-hour availability metrics produced by build_youbike_peak_dashboard.py.

CREATE TABLE IF NOT EXISTS public.youbike_peak_station_metrics (
    ogc_fid             serial PRIMARY KEY,
    station_id          text,
    station_name        text,
    city                text,
    area                text,
    address             text,
    capacity            integer,
    lat                 double precision,
    lon                 double precision,
    segment             text,
    role                text,
    sample_count        integer,
    date_count          integer,
    avg_bike_rate       double precision,
    avg_dock_rate       double precision,
    has_bike_rate       double precision,
    has_dock_rate       double precision,
    zero_bike_rate      double precision,
    zero_dock_rate      double precision,
    avg_available_bikes double precision,
    avg_available_docks double precision,
    imbalance_rate      double precision,
    imbalance_abs       double precision,
    generated_at        timestamp with time zone,
    _ctime              timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS youbike_peak_metrics_segment_idx
    ON public.youbike_peak_station_metrics (segment);

CREATE INDEX IF NOT EXISTS youbike_peak_metrics_role_idx
    ON public.youbike_peak_station_metrics (role);

CREATE INDEX IF NOT EXISTS youbike_peak_metrics_city_idx
    ON public.youbike_peak_station_metrics (city);
