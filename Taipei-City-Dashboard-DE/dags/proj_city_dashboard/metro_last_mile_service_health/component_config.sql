-- Register the Metro Taipei last-mile service health component.
-- Run this in the dashboardmanager database after table_schema.sql has been
-- applied to the dashboard database.

BEGIN;

-- Remove only the records owned by this component so this file is idempotent.
DELETE FROM public.dashboard_groups
WHERE dashboard_id IN (
    SELECT id
    FROM public.dashboards
    WHERE "index" = 'commute_last_mile_metrotaipei'
);

DELETE FROM public.dashboards
WHERE "index" = 'commute_last_mile_metrotaipei';

DELETE FROM public.query_charts
WHERE "index" = 'metro_last_mile_service_health'
  AND city = 'metrotaipei';

DELETE FROM public.component_maps
WHERE id BETWEEN 990010 AND 990019
   OR "index" LIKE 'metro_last_mile_%';

DELETE FROM public.component_charts
WHERE "index" = 'metro_last_mile_service_health';

DELETE FROM public.components
WHERE "index" = 'metro_last_mile_service_health';

INSERT INTO public.components ("id", "index", "name")
VALUES (990001, 'metro_last_mile_service_health', '捷運最後一哩服務健康度');

INSERT INTO public.component_charts ("index", "color", "types", "unit")
VALUES (
    'metro_last_mile_service_health',
    ARRAY['#39c5bb', '#7ea1ff', '#f4b942', '#ef6f6c', '#c48c31'],
    ARRAY['MetroLastMileLineChart'],
    '分'
);

INSERT INTO public.component_maps (
    "id",
    "index",
    "title",
    "type",
    "source",
    "size",
    "icon",
    "paint",
    "property"
)
VALUES
(
    990010,
    'metro_last_mile_br_route',
    '文湖線',
    'line',
    'geojson',
    'wide',
    NULL,
    '{"line-color": ["match", ["get", "line_id"], "BR", "#c48c31", "#8a94a6"], "line-opacity": 0.78, "line-width": ["interpolate", ["linear"], ["zoom"], 10.99, 2.8, 13, 5.5, 18, 9.5]}'::json,
    '[{"key":"line_name","name":"捷運路線"},{"key":"line_id","name":"路線代碼"},{"key":"data_time","name":"資料時間"}]'::json
),
(
    990011,
    'metro_last_mile_br_stations',
    '文湖線',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "service_status"], "good", "#39c5bb", "watch", "#7ea1ff", "weak", "#f4b942", "failing", "#ef6f6c", "#8a94a6"], "circle-radius": ["interpolate", ["linear"], ["get", "risk_score"], 0, 4, 20, 7, 40, 11, 60, 15, 80, 19, 100, 23], "circle-opacity": 0.86, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10.99, 0.4, 14, 1.2, 18, 2]}'::json,
    '[{"key":"station_name","name":"捷運站"},{"key":"line_name","name":"路線"},{"key":"service_score","name":"服務健康度"},{"key":"risk_score","name":"接駁風險"},{"key":"status_label","name":"狀態"},{"key":"bike_station_count","name":"YouBike站數"},{"key":"available_rent_bikes","name":"可借車"},{"key":"available_return_bikes","name":"可還位"},{"key":"median_eta_min","name":"公車ETA中位數"}]'::json
),
(
    990012,
    'metro_last_mile_r_route',
    '淡水信義線',
    'line',
    'geojson',
    'wide',
    NULL,
    '{"line-color": ["match", ["get", "line_id"], "R", "#e3002c", "#8a94a6"], "line-opacity": 0.78, "line-width": ["interpolate", ["linear"], ["zoom"], 10.99, 2.8, 13, 5.5, 18, 9.5]}'::json,
    '[{"key":"line_name","name":"捷運路線"},{"key":"line_id","name":"路線代碼"},{"key":"data_time","name":"資料時間"}]'::json
),
(
    990013,
    'metro_last_mile_r_stations',
    '淡水信義線',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "service_status"], "good", "#39c5bb", "watch", "#7ea1ff", "weak", "#f4b942", "failing", "#ef6f6c", "#8a94a6"], "circle-radius": ["interpolate", ["linear"], ["get", "risk_score"], 0, 4, 20, 7, 40, 11, 60, 15, 80, 19, 100, 23], "circle-opacity": 0.86, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10.99, 0.4, 14, 1.2, 18, 2]}'::json,
    '[{"key":"station_name","name":"捷運站"},{"key":"line_name","name":"路線"},{"key":"service_score","name":"服務健康度"},{"key":"risk_score","name":"接駁風險"},{"key":"status_label","name":"狀態"},{"key":"bike_station_count","name":"YouBike站數"},{"key":"available_rent_bikes","name":"可借車"},{"key":"available_return_bikes","name":"可還位"},{"key":"median_eta_min","name":"公車ETA中位數"}]'::json
),
(
    990014,
    'metro_last_mile_g_route',
    '松山新店線',
    'line',
    'geojson',
    'wide',
    NULL,
    '{"line-color": ["match", ["get", "line_id"], "G", "#008659", "#8a94a6"], "line-opacity": 0.78, "line-width": ["interpolate", ["linear"], ["zoom"], 10.99, 2.8, 13, 5.5, 18, 9.5]}'::json,
    '[{"key":"line_name","name":"捷運路線"},{"key":"line_id","name":"路線代碼"},{"key":"data_time","name":"資料時間"}]'::json
),
(
    990015,
    'metro_last_mile_g_stations',
    '松山新店線',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "service_status"], "good", "#39c5bb", "watch", "#7ea1ff", "weak", "#f4b942", "failing", "#ef6f6c", "#8a94a6"], "circle-radius": ["interpolate", ["linear"], ["get", "risk_score"], 0, 4, 20, 7, 40, 11, 60, 15, 80, 19, 100, 23], "circle-opacity": 0.86, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10.99, 0.4, 14, 1.2, 18, 2]}'::json,
    '[{"key":"station_name","name":"捷運站"},{"key":"line_name","name":"路線"},{"key":"service_score","name":"服務健康度"},{"key":"risk_score","name":"接駁風險"},{"key":"status_label","name":"狀態"},{"key":"bike_station_count","name":"YouBike站數"},{"key":"available_rent_bikes","name":"可借車"},{"key":"available_return_bikes","name":"可還位"},{"key":"median_eta_min","name":"公車ETA中位數"}]'::json
),
(
    990016,
    'metro_last_mile_o_route',
    '中和新蘆線',
    'line',
    'geojson',
    'wide',
    NULL,
    '{"line-color": ["match", ["get", "line_id"], "O", "#f8b61c", "#8a94a6"], "line-opacity": 0.78, "line-width": ["interpolate", ["linear"], ["zoom"], 10.99, 2.8, 13, 5.5, 18, 9.5]}'::json,
    '[{"key":"line_name","name":"捷運路線"},{"key":"line_id","name":"路線代碼"},{"key":"data_time","name":"資料時間"}]'::json
),
(
    990017,
    'metro_last_mile_o_stations',
    '中和新蘆線',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "service_status"], "good", "#39c5bb", "watch", "#7ea1ff", "weak", "#f4b942", "failing", "#ef6f6c", "#8a94a6"], "circle-radius": ["interpolate", ["linear"], ["get", "risk_score"], 0, 4, 20, 7, 40, 11, 60, 15, 80, 19, 100, 23], "circle-opacity": 0.86, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10.99, 0.4, 14, 1.2, 18, 2]}'::json,
    '[{"key":"station_name","name":"捷運站"},{"key":"line_name","name":"路線"},{"key":"service_score","name":"服務健康度"},{"key":"risk_score","name":"接駁風險"},{"key":"status_label","name":"狀態"},{"key":"bike_station_count","name":"YouBike站數"},{"key":"available_rent_bikes","name":"可借車"},{"key":"available_return_bikes","name":"可還位"},{"key":"median_eta_min","name":"公車ETA中位數"}]'::json
),
(
    990018,
    'metro_last_mile_bl_route',
    '板南線',
    'line',
    'geojson',
    'wide',
    NULL,
    '{"line-color": ["match", ["get", "line_id"], "BL", "#0070bd", "#8a94a6"], "line-opacity": 0.78, "line-width": ["interpolate", ["linear"], ["zoom"], 10.99, 2.8, 13, 5.5, 18, 9.5]}'::json,
    '[{"key":"line_name","name":"捷運路線"},{"key":"line_id","name":"路線代碼"},{"key":"data_time","name":"資料時間"}]'::json
),
(
    990019,
    'metro_last_mile_bl_stations',
    '板南線',
    'circle',
    'geojson',
    NULL,
    NULL,
    '{"circle-color": ["match", ["get", "service_status"], "good", "#39c5bb", "watch", "#7ea1ff", "weak", "#f4b942", "failing", "#ef6f6c", "#8a94a6"], "circle-radius": ["interpolate", ["linear"], ["get", "risk_score"], 0, 4, 20, 7, 40, 11, 60, 15, 80, 19, 100, 23], "circle-opacity": 0.86, "circle-stroke-color": "#ffffff", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 10.99, 0.4, 14, 1.2, 18, 2]}'::json,
    '[{"key":"station_name","name":"捷運站"},{"key":"line_name","name":"路線"},{"key":"service_score","name":"服務健康度"},{"key":"risk_score","name":"接駁風險"},{"key":"status_label","name":"狀態"},{"key":"bike_station_count","name":"YouBike站數"},{"key":"available_rent_bikes","name":"可借車"},{"key":"available_return_bikes","name":"可還位"},{"key":"median_eta_min","name":"公車ETA中位數"}]'::json
);

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
    'metro_last_mile_service_health',
    '{"color": ["#39c5bb", "#7ea1ff", "#f4b942", "#ef6f6c", "#c48c31"], "range": ["day_ago", "week_ago", "month_ago"], "unit": "分"}'::json,
    ARRAY[990010,990011,990012,990013,990014,990015,990016,990017,990018,990019]::integer[],
    '{"mode": "byLayer", "byParam": null}'::json,
    'current',
    NULL,
    5,
    'minute',
    'TDX / 臺北城市儀表板捷運路網 GeoJSON',
    '顯示雙北捷運站 500 公尺最後一哩接駁圈是否正在正常服務。',
    '此組件以捷運站周邊 500 公尺作為最後一哩接駁圈，整合 YouBike 取車可用、還車可用、公車 ETA 可靠度與接駁覆蓋，計算 0 到 100 分的服務健康度。分數越低表示出站後接駁失效風險越高。地圖以顏色表示狀態，並以圓圈大小表示風險分數。',
    '民眾可判斷出站後 YouBike 或公車接駁是否穩定；政府可用於 YouBike 調度、接駁公車加密、站區轉乘設施改善，以及在地圖上與其他交通圖層交叉比對。',
    ARRAY[
        'https://tdx.transportdata.tw/',
        'https://citydashboard.taipei/dashboard'
    ],
    ARRAY['codefest'],
    NOW(),
    NOW(),
    'two_d',
    $$
    WITH latest AS (
        SELECT MAX(data_time) AS data_time
        FROM public.metro_last_mile_service_health
    ),
    line_order AS (
        SELECT *
        FROM (VALUES
            ('文湖線', 1),
            ('淡水信義線', 2),
            ('松山新店線', 3),
            ('中和新蘆線', 4),
            ('板南線', 5)
        ) AS line_order(line_name, ord)
    )
    SELECT
        line_order.line_name || '｜' || t.station_name AS x_axis,
        ROUND(t.service_score::numeric, 1)::float AS data
    FROM public.metro_last_mile_service_health t
    JOIN latest ON t.data_time = latest.data_time
    JOIN line_order ON t.line_name = line_order.line_name
    ORDER BY line_order.ord, t.service_score DESC, t.station_name
    $$,
    $$
    SELECT
        date_trunc('%s', data_time) AS x_axis,
        line_name AS y_axis,
        ROUND(AVG(service_score)::numeric, 1)::float AS data
    FROM public.metro_last_mile_service_health_history
    WHERE data_time BETWEEN '%s' AND '%s'
    GROUP BY x_axis, line_name
    ORDER BY x_axis, line_name
    $$,
    'metrotaipei'
);

INSERT INTO public.contributors (
    "id",
    "user_id",
    "user_name",
    "image",
    "link",
    "identity",
    "description",
    "include",
    "created_at",
    "updated_at"
)
VALUES (
    990001,
    'codefest',
    'Codefest 2026',
    'codefest.png',
    'https://citydashboard.taipei/dashboard',
    '資料應用原型',
    '捷運最後一哩服務健康度組件資料與方法設計。',
    FALSE,
    NOW(),
    NOW()
)
ON CONFLICT ("id") DO UPDATE
SET
    "user_id" = EXCLUDED."user_id",
    "user_name" = EXCLUDED."user_name",
    "image" = EXCLUDED."image",
    "link" = EXCLUDED."link",
    "identity" = EXCLUDED."identity",
    "description" = EXCLUDED."description",
    "updated_at" = NOW();

INSERT INTO public.dashboards (
    "id",
    "index",
    "name",
    "components",
    "icon",
    "created_at",
    "updated_at"
)
VALUES (
    990001,
    'commute_last_mile_metrotaipei',
    '通勤最後一哩',
    ARRAY[990001]::integer[],
    'directions_transit',
    NOW(),
    NOW()
);

INSERT INTO public.dashboard_groups ("dashboard_id", "group_id")
SELECT 990001, id
FROM public.groups
WHERE name = 'metrotaipei'
ON CONFLICT DO NOTHING;

COMMIT;

