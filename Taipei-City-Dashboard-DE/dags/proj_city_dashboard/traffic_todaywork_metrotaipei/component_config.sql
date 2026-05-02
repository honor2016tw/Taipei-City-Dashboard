-- Register the Metro Taipei variant of component 20 / traffic_todaywork.
-- Run this in the dashboardmanager database after the base Taipei component exists.

INSERT INTO public.components ("id", "index", "name")
VALUES (20, 'traffic_todaywork', '道路施工')
ON CONFLICT ("id") DO NOTHING;

INSERT INTO public.component_charts ("index", "color", "types", "unit")
VALUES ('traffic_todaywork', ARRAY['#2f9ca1'], ARRAY['DistrictChart', 'BarChart'], '件')
ON CONFLICT ("index") DO NOTHING;

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

DELETE FROM public.query_charts
WHERE "index" = 'traffic_todaywork'
  AND "city" = 'metrotaipei';

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
    'traffic_todaywork',
    '{"color": null, "range": ["quarter_ago", "halfyear_ago", "year_ago"], "unit": "件"}'::json,
    ARRAY[20020]::integer[],
    '{"mode": "byParam", "byParam": {"xParam": "district", "yParam": null}}'::json,
    'current',
    NULL,
    10,
    'minute',
    '臺北市政府工務局 / 新北市政府開放資料',
    '顯示目前雙北道路施工與道路挖掘案件的行政區分布。',
    '整合臺北市今日施工資訊與新北市道路挖掘案件資料，統計目前雙北各行政區的施工案件數。臺北市資料取自臺北市政府工務局 Todaywork.json；新北市資料取自新北市政府開放資料「新北市政府道路挖掘資訊」CSV API，並以案件施工起訖日期判斷今日仍有效的案件。圖表可切換行政區圖與橫向長條圖，用於快速掌握施工熱區與跨市通勤路廊可能受影響的位置。',
    '通勤者可在出門前查看雙北哪些行政區施工案件較多，避開施工密集區域；交通或工務單位可用來比較各行政區施工量，作為道路施工告示、交通疏導與跨縣市協調的參考。',
    ARRAY[
        'https://data.taipei/dataset/detail?id=c208dabd-2da0-4e6d-8dbd-a004b9782b0a',
        'https://data.ntpc.gov.tw/api/datasets/96b6101b-c033-4834-8bd5-e312651db7a0/csv?page=0&size=100'
    ],
    ARRAY['tuic'],
    NOW(),
    NOW(),
    'two_d',
    $$
    WITH districts AS (
        SELECT *
        FROM unnest(ARRAY[
            '北投區', '士林區', '內湖區', '南港區', '松山區', '信義區',
            '中山區', '大同區', '中正區', '萬華區', '大安區', '文山區',
            '新莊區', '淡水區', '汐止區', '板橋區', '三重區', '樹林區',
            '土城區', '蘆洲區', '中和區', '永和區', '新店區', '鶯歌區',
            '三峽區', '瑞芳區', '五股區', '泰山區', '林口區', '深坑區',
            '石碇區', '坪林區', '三芝區', '石門區', '八里區', '平溪區',
            '雙溪區', '貢寮區', '金山區', '萬里區', '烏來區'
        ]::varchar[]) WITH ORDINALITY AS d(x_axis, ord)
    ),
    construction_counts AS (
        SELECT district AS x_axis, COUNT(*)::float AS data
        FROM traffic_todayworks_metrotaipei
        GROUP BY district
    )
    SELECT districts.x_axis, COALESCE(construction_counts.data, 0) AS data
    FROM districts
    LEFT JOIN construction_counts USING (x_axis)
    ORDER BY districts.ord
    $$,
    $$
    SELECT date_trunc('%s', data_time) AS x_axis,
           '施工案件' AS y_axis,
           COUNT(*)::float AS data
    FROM traffic_todayworks_metrotaipei_history
    WHERE data_time BETWEEN '%s' AND '%s'
    GROUP BY x_axis
    ORDER BY x_axis
    $$,
    'metrotaipei'
);
