# 雨天通勤崩潰放大係數儀表板組件

這個資料夾是「先不動外部專案」的組件化輸出，可用來對照臺北城市儀表板的 component config / chart data 概念。

## 檔案

- `component_config.json`：組件 metadata，欄位參考臺北城市儀表板 component config。
- `chart_data.json`：Top 10 站點壓力拆解，格式接近 three_d chart data。
- `metro_network_data.json`：捷運路網、站點 RLCAF 與各子壓力，供自訂 Metro/Network 元件使用。
- `widget.html`：可用 iframe 方式嵌入的組件頁。
- `widget.css`、`widget.js`：嵌入組件的樣式與渲染邏輯。

## 嵌入方式

```html
<iframe
  src="./dashboard_component/widget.html"
  title="雨天通勤崩潰放大係數"
  style="width: 100%; height: 720px; border: 0;"
></iframe>
```

## 計算定義

```text
RLCAF(s,t) =
RainLastMilePressure(s,t)
/
NonRainBaselinePressure(s,dow,time_slot)
```

其中 `s` 是捷運站，`t` 是目前時間。空間單位採捷運站周邊 500 公尺，依據是共享單車作為捷運最後一哩補充工具的研究中，利用 buffer 邊際密度轉折點決定捷運站共享單車影響範圍的做法。

目前 MVP 的最後一哩壓力由四個已可對齊雙北的子壓力組成：

- YouBike 取車失敗
- YouBike 還車失敗
- 公車延誤
- 雨天步行懲罰

道路干擾保留欄位，但在雙北即時覆蓋不一致前不納入主指標。
