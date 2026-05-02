# 捷運最後一哩服務健康度儀表板組件

這個資料夾是「先不動外部專案」的組件化輸出，可用來對照臺北城市儀表板的 component config / chart data 概念。

## 檔案

- `component_config.json`：組件 metadata，欄位參考臺北城市儀表板 component config。
- `chart_data.json`：弱服務站點、城市摘要與權重設定。
- `metro_network_data.json`：捷運路線 GeoJSON 與站點服務健康度，供自訂 Metro/Network 元件使用。
- `widget.html`：可用 iframe 方式嵌入的組件頁。
- `widget.css`、`widget.js`：嵌入組件的樣式與渲染邏輯。

## 嵌入方式

```html
<iframe
  src="./dashboard_component/widget.html"
  title="捷運最後一哩服務健康度"
  style="width: 100%; height: 720px; border: 0;"
></iframe>
```

## 計算定義

```text
ServiceHealth(s,t) =
100 * (
  0.30 * BikePickupAvailability
+ 0.25 * BikeReturnAvailability
+ 0.30 * BusReliability
+ 0.15 * CoverageResilience
)
```

其中 `s` 是捷運站，`t` 是目前快照時間。空間單位採捷運站周邊 500 公尺，依據是共享單車作為捷運最後一哩補充工具的研究中，利用 buffer 邊際密度轉折點決定捷運站共享單車影響範圍的做法。

目前 MVP 的服務健康度由四個已可對齊雙北的子指標組成：

- YouBike 取車可用
- YouBike 還車可用
- 公車即時可靠度
- 替代接駁覆蓋

路網使用 `metro_routes/*.geojson` 的實際路線 geometry，不再用站點排序硬連線。
