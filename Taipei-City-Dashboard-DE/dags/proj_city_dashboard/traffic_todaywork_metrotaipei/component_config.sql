-- Register the Metro Taipei variant of component 20 / traffic_todaywork.
-- Run this in the dashboardmanager database after the base Taipei component exists.

INSERT INTO public.components ("id", "index", "name")
VALUES (20, 'traffic_todaywork', '道路施工')
ON CONFLICT ("id") DO NOTHING;

INSERT INTO public.component_charts ("index", "color", "types", "unit")
VALUES ('traffic_todaywork', ARRAY['#2f9ca1'], ARRAY['DistrictChart', 'BarChart'], '件')
ON CONFLICT ("index") DO NOTHING;

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
    NULL,
    NULL,
    '2026-05-02T00:00:00+08:00',
    NULL,
    10,
    'minute',
    '工務局 / 新北市政府養護工程處',
    '顯示當前雙北道路施工的數量統計',
    '顯示當前雙北道路施工的數量統計，臺北市資料來源為工務局 Todaywork.json，新北市資料來源為 iROAD 道路工程案件，每10分鐘更新。',
    '圖表呈現雙北各行政區施工數量統計，可切換行政區圖與橫向長條圖檢視分布。',
    ARRAY[
        'https://data.taipei/dataset/detail?id=c208dabd-2da0-4e6d-8dbd-a004b9782b0a',
        'https://roadmt.maintenance.ntpc.gov.tw/iROAD/Home/GetCaseRoadConst'
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
