# 捷運最後一哩服務健康度方法說明

## 指標問題

本版指標不先回答「雨天造成幾倍放大」，而是先回答一個更即時的營運問題：

```text
同一個捷運站周邊，現在出站後的最後一哩接駁還能不能正常服務？
```

正式名稱：

```text
Metro Last-mile Service Health
```

雨天可以保留為後續情境濾鏡，但主指標先聚焦即時服務能力，避免在歷史 baseline 還不足時硬做因果倍率。

## 文獻轉譯

依使用者提供的共享單車與捷運轉乘研究摘要，本專案保留三個有文獻支撐的方法假設：

1. 共享單車是捷運最後一哩的重要補充工具，因此捷運服務是否順暢不能只看列車本身，也要看出站後 YouBike 與接駁公車是否仍可用。
2. 捷運站影響範圍採 500 公尺 buffer。研究以共享單車旅次隨 buffer 面積增加的邊際密度變化選取轉折點，MVP 先採 500m，後續可用雙北 YouBike 歷史旅次重新校正。
3. 不同捷運站具有不同時段型態，因此排名與趨勢解讀應保留站型資訊，例如轉乘型、通勤型、商圈混合型、郊區型。

Buffer 邊際密度概念：

```text
increase_Den_j =
(D_{j+1} - D_j) / [pi * (R_{j+1}^2 - R_j^2)]
```

## 核心公式

```text
ServiceHealth(s,t) =
100 * (
  0.30 * BikePickupAvailability(s,t)
+ 0.25 * BikeReturnAvailability(s,t)
+ 0.30 * BusReliability(s,t)
+ 0.15 * CoverageResilience(s,t)
)
```

其中：

- `s`：捷運站。
- `t`：目前資料快照時間。
- 分數範圍為 0 到 100。
- 分數越高代表最後一哩服務越穩定；分數越低代表出站後接駁失效風險越高。

## 子指標

### YouBike 取車可用

衡量捷運站 500m 內 YouBike 站點是否還有車可借：

```text
BikePickupAvailability =
median(available_bikes_i / total_docks_i) - offline_penalty
```

若只使用既有快照欄位，則可用：

```text
BikePickupAvailability = 1 - no_bike_rate
```

### YouBike 還車可用

衡量騎到站區後是否還有空位可還：

```text
BikeReturnAvailability =
median(available_docks_i / total_docks_i) - offline_penalty
```

若只使用既有快照欄位，則可用：

```text
BikeReturnAvailability = 1 - no_return_rate
```

### 公車即時可靠度

公車接駁同時看等待時間與站牌異常率：

```text
ETA_score = max(0, 1 - median_eta_minutes / 25)

BusReliability =
0.72 * ETA_score
+ 0.28 * (1 - bus_issue_rate)
```

25 分鐘以上的中位等待時間會視為高度不可靠。這不是永久標準，正式版可依各站歷史分位數校正。

### 替代接駁覆蓋

若站區本身 YouBike 站與公車站都很少，即使當下沒有異常，也代表韌性較低：

```text
CoverageResilience =
0.45 * min(1, bike_station_count / 6)
+ 0.55 * min(1, bus_stop_count / 35)
```

## 判讀

```text
80-100：服務穩定
65-79 ：需觀察
50-64 ：服務偏弱
0-49  ：接駁失效風險高
```

目前門檻是 MVP 的直觀營運門檻。正式版可改成同站、同星期、同時段歷史分位數，例如低於第 20 分位視為弱服務。

## 站型

MVP 先以規則式分類：

- `轉乘型站`：捷運 line degree >= 2。
- `通勤型站`：公車站與 YouBike 站密度都高。
- `商圈混合型站`：YouBike 站密度高。
- `郊區型站`：公車站與 YouBike 站都少。
- `一般接駁型站`：其他。

正式版可依論文方法使用 hourly bike-sharing trips 抽特徵，再用 K-means 與 silhouette coefficient 找站型。

## 捷運路網

地圖不再用站點排序硬連線。前端讀取 `current_data.json` 裡的 `metro_routes`，其內容來自 `metro_routes/*.geojson`，以實際路線 MultiLineString 畫捷運線形，再疊加捷運站服務健康度。

## 與雨天版本的關係

本版不是否定雨天議題，而是把服務基礎打穩：

```text
先做 Last-mile Service Health
再把天氣狀態作為情境條件或濾鏡
最後才視需要比較特定天氣下的服務風險與平常服務基準
```

這樣資料邏輯比較穩，也比較符合即時儀表板的使用情境。
