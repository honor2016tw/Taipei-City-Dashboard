-- Enable spatial data for component 20 / traffic_todaywork.
-- Run this in the dashboardmanager database.
-- The frontend must also have:
--   public/mapData/traffic_todaywork_metrotaipei.geojson

BEGIN;

DELETE FROM public.component_maps
WHERE "id" = 20020
   OR "index" = 'traffic_todaywork_metrotaipei';

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
VALUES (
    20020,
    'traffic_todaywork_metrotaipei',
    '今日道路施工位置',
    'circle',
    'geojson',
    'big',
    NULL,
    '{"circle-color": ["match", ["get", "source_city"], "臺北市", "#2f9ca1", "新北市", "#5b8cff", "#9aa0a6"], "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 4, 13, 7, 16, 11], "circle-opacity": 0.82, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1}'::json,
    '[{"key":"source_city","name":"縣市"},{"key":"district","name":"行政區"},{"key":"project_name","name":"工程名稱"},{"key":"organizer","name":"主辦單位"},{"key":"address","name":"施工位置"},{"key":"date_range","name":"施工日期"},{"key":"source","name":"資料來源"}]'::json
);

UPDATE public.query_charts
SET
    map_config_ids = ARRAY[20020]::integer[],
    map_filter = '{"mode": "byParam", "byParam": {"xParam": "district", "yParam": null}}'::json,
    updated_at = NOW()
WHERE "index" = 'traffic_todaywork'
  AND city = 'metrotaipei';

COMMIT;

SELECT
    qc."index",
    qc.city,
    qc.map_config_ids,
    qc.map_filter,
    cm."index" AS map_index,
    cm.title,
    cm.type,
    cm.source
FROM public.query_charts qc
LEFT JOIN public.component_maps cm
    ON cm.id = ANY(qc.map_config_ids)
WHERE qc."index" = 'traffic_todaywork'
  AND qc.city = 'metrotaipei';
