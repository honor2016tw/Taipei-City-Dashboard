-- Register the YouBike Peak Pressure component in the dashboardmanager database.
-- Run this against the dashboardmanager (postgres-manager) database.
-- This file is idempotent: it removes existing records before re-inserting.

BEGIN;

DELETE FROM public.dashboard_groups
WHERE dashboard_id = 990002;

DELETE FROM public.query_charts
WHERE "index" = 'youbike_peak_pressure';

DELETE FROM public.component_maps
WHERE id = 990020;

DELETE FROM public.component_charts
WHERE "index" = 'youbike_peak_pressure';

DELETE FROM public.components
WHERE "index" = 'youbike_peak_pressure';

-- Component
INSERT INTO public.components ("id", "index", "name")
VALUES (990002, 'youbike_peak_pressure', 'YouBike尖峰壓力站分佈');

-- Chart config
-- Color order matches SQL x_axis sort: 借車壓力站 / 平衡站 / 還車壓力站
INSERT INTO public.component_charts ("index", "color", "types", "unit")
VALUES (
    'youbike_peak_pressure',
    ARRAY['#E25555', '#18B7A7', '#F2A93B'],
    ARRAY['YouBikePeakSegmentChart'],
    '站'
);

-- Map layer: circle colored by role
INSERT INTO public.component_maps (
    "id", "index", "title", "type", "source", "size", "icon", "paint", "property"
)
VALUES (
    990020,
    'youbike_peak_pressure_stations',
    'YouBike尖峰壓力站',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "role"], "借車壓力站", "#E25555", "還車壓力站", "#F2A93B", "#18B7A7"], "circle-radius": 4, "circle-opacity": 0.78, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 11, 0.3, 15, 1.2]}'::json,
    '[{"key":"name","name":"站名"},{"key":"area","name":"行政區"},{"key":"city","name":"城市"},{"key":"segment","name":"時段"},{"key":"role","name":"壓力角色"},{"key":"avg_bike_rate","name":"平均可借率"},{"key":"avg_dock_rate","name":"平均可還率"}]'::json
);

-- Query chart (three_d: x_axis=role, y_axis=segment)
INSERT INTO public.query_charts (
    "index",
    "history_config",
    "map_config_ids",
    "map_filter",
    "time_from",
    "time_to",
    "update_freq",
    "update_freq_unit",
    "source",
    "short_desc",
    "long_desc",
    "use_case",
    "links",
    "contributors",
    "created_at",
    "updated_at",
    "query_type",
    "query_chart",
    "query_history",
    "city"
)
VALUES (
    'youbike_peak_pressure',
    NULL,
    ARRAY[990020]::integer[],
    '{"mode": "byParam", "byParam": null}'::json,
    'static',
    NULL,
    0,
    'day',
    '臺北市政府 YouBike 即時資料 / 新北市政府 OpenData',
    '雙北 YouBike 站點於各尖峰時段的壓力角色分佈，可切換平日/週末 × 早/晚高峰。',
    '依各時段多次快照統計，將雙北 3,260 個站點分類為借車壓力站、還車壓力站或平衡站，呈現車站結構失衡情形。借車壓力站表示車多，可借車少；還車壓力站表示空位多，可還位少。',
    '提供調度決策依據：借車壓力站需在尖峰前補充車輛，還車壓力站需優先清空歸還位。地圖圖層可交叉比對各站位置與捷運路網。',
    ARRAY[
        'https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json',
        'https://data.ntpc.gov.tw/api/datasets/010E5B15-3823-4B20-B401-B1CF000550C5/json'
    ],
    ARRAY['codefest'],
    NOW(),
    NOW(),
    'three_d',
    $$
    SELECT role AS x_axis, segment AS y_axis, COUNT(*) AS data
    FROM public.youbike_peak_station_metrics
    GROUP BY role, segment
    ORDER BY x_axis, y_axis
    $$,
    NULL,
    'metrotaipei'
);

-- ── 台北市地圖圖層（NTPC 透明，只顯示 TPE 站點）────────────────────────────────
DELETE FROM public.component_maps WHERE id = 990021;

INSERT INTO public.component_maps (
    "id", "index", "title", "type", "source", "size", "icon", "paint", "property"
)
VALUES (
    990021,
    'youbike_peak_pressure_stations',
    'YouBike尖峰壓力站（臺北市）',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "role"], "借車壓力站", "#E25555", "還車壓力站", "#F2A93B", "#18B7A7"], "circle-radius": 4, "circle-opacity": ["match", ["get", "city"], "TPE", 0.78, 0], "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 11, 0.3, 15, 1.2]}'::json,
    '[{"key":"name","name":"站名"},{"key":"area","name":"行政區"},{"key":"city","name":"城市"},{"key":"segment","name":"時段"},{"key":"role","name":"壓力角色"},{"key":"avg_bike_rate","name":"平均可借率"},{"key":"avg_dock_rate","name":"平均可還率"}]'::json
);

-- ── 台北市 (taipei) 城市變體 ──────────────────────────────────────────────────
DELETE FROM public.query_charts
WHERE "index" = 'youbike_peak_pressure'
  AND "city" = 'taipei';

INSERT INTO public.query_charts (
    "index",
    "history_config",
    "map_config_ids",
    "map_filter",
    "time_from",
    "time_to",
    "update_freq",
    "update_freq_unit",
    "source",
    "short_desc",
    "long_desc",
    "use_case",
    "links",
    "contributors",
    "created_at",
    "updated_at",
    "query_type",
    "query_chart",
    "query_history",
    "city"
)
VALUES (
    'youbike_peak_pressure',
    NULL,
    ARRAY[990021]::integer[],
    '{"mode": "byParam", "byParam": null}'::json,
    'static',
    NULL,
    0,
    'day',
    '臺北市政府 YouBike 即時資料',
    '臺北市 YouBike 站點於各尖峰時段的壓力角色分佈，可切換平日/週末 × 早/晚高峰。',
    '依各時段多次快照統計，將臺北市站點分類為借車壓力站、還車壓力站或平衡站，呈現車站結構失衡情形。借車壓力站表示車多，可借車少；還車壓力站表示空位多，可還位少。',
    '提供臺北市調度決策依據：借車壓力站需在尖峰前補充車輛，還車壓力站需優先清空歸還位。地圖圖層可交叉比對各站位置與捷運路網。',
    ARRAY[
        'https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json'
    ],
    ARRAY['codefest'],
    NOW(),
    NOW(),
    'three_d',
    $$
    SELECT role AS x_axis, segment AS y_axis, COUNT(*) AS data
    FROM public.youbike_peak_station_metrics
    WHERE city = 'TPE'
    GROUP BY role, segment
    ORDER BY x_axis, y_axis
    $$,
    NULL,
    'taipei'
);

-- Add component 990002 to the Codefest dashboard
UPDATE public.dashboards
SET components = array_append(components, 990002)
WHERE "index" = 'commute_last_mile_metrotaipei'
  AND NOT (components @> ARRAY[990002]::integer[]);

COMMIT;
