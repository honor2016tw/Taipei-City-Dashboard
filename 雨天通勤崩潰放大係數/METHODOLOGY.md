# 雨天通勤崩潰放大係數方法說明

## 指標問題

本指標不回答「現在是否下雨」，而是回答：

```text
同一個捷運站、同一星期、同一時段，雨天讓最後一哩接駁壓力放大幾倍？
```

正式名稱：

```text
Rain-induced Last-mile Collapse Amplification Factor, RLCAF
```

## 文獻轉譯

依使用者提供的共享單車與捷運轉乘研究摘要，本專案採用三個方法假設：

1. 共享單車是捷運最後一哩的重要補充工具，因此雨天通勤風險應觀察捷運站出站後的接駁圈，而不只看道路速度。
2. 捷運站影響範圍採 500 公尺 buffer。研究以共享單車旅次隨 buffer 面積增加的邊際密度變化選取轉折點，MVP 先採 500m，後續可用雙北 YouBike 歷史旅次重新校正。
3. 不同捷運站具有不同時段型態，因此 baseline 必須使用同站、同星期、同時段的非雨天歷史中位數，而不是全市平均或全日平均。

Buffer 邊際密度概念：

```text
increase_Den_j =
(D_{j+1} - D_j) / [pi * (R_{j+1}^2 - R_j^2)]
```

## 核心公式

```text
RLCAF(s,t) =
RainLastMilePressure(s,t)
/
NonRainBaselinePressure(s,dow,time_slot)
```

其中：

- `s`：捷運站。
- `t`：目前時間。
- `dow`：星期幾。
- `time_slot`：目前 MVP 使用小時，後續可改成 07:00-09:00、17:00-19:00 等時段。
- `NonRainBaselinePressure`：本機歷史快照中，同站、同星期、同時段、非雨天壓力的中位數。

## 最後一哩壓力

MVP 的 `RainLastMilePressure` 由四個已能雙北對齊的子壓力組成，並保留道路干擾欄位：

```text
RainLastMilePressure =
  0.25 * BikePickupFailure
+ 0.25 * BikeReturnFailure
+ 0.25 * BusDelayPressure
+ 0.15 * WalkRainPenalty
+ 0.10 * RoadInterferencePressure
```

目前 `RoadInterferencePressure` 因雙北即時道路資料覆蓋不一致，設為 `null`，計算時會在可用子項間重新正規化權重，不用缺資料硬估。

## 子壓力

### YouBike 取車失敗

```text
BikePickupFailure =
1 - median(available_bikes_i / total_docks_i)
```

`i` 為捷運站 500m 內的 YouBike 站點。若站點離線，會加入小幅懲罰。

### YouBike 還車失敗

```text
BikeReturnFailure =
1 - median(available_docks_i / total_docks_i)
```

這代表「騎得到但還不了」的最後一哩失敗。

### 公車延誤壓力

```text
BusDelayPressure =
0.75 * min(median_eta_minutes / 20, 1)
+ 0.25 * bus_issue_rate
```

正式版可改成：

```text
median(CurrentBusETA / NonRainBusETA_baseline)
```

但目前 component baseline 仍在累積，因此 MVP 先用即時 ETA 中位數與站牌異常率。

### 雨天步行懲罰

```text
WalkRainPenalty =
min(1, rain_mm / 10) * (avg_transfer_distance / 500)
```

目前雨量使用 Open-Meteo 逐時降雨。若接上雨量站 10/30/60 分鐘資料，可替換為：

```text
RainIntensity =
0.5 * rain_10min
+ 0.3 * rain_30min
+ 0.2 * rain_60min
```

## 站型

MVP 先以規則式分類：

- `轉乘型站`：捷運 line degree >= 2。
- `通勤型站`：公車站與 YouBike 站密度都高。
- `商圈混合型站`：YouBike 站密度高。
- `郊區型站`：公車站與 YouBike 站都少。
- `一般接駁型站`：其他。

正式版可依論文方法使用 hourly bike-sharing trips 抽特徵，再用 K-means 與 silhouette coefficient 找站型。
