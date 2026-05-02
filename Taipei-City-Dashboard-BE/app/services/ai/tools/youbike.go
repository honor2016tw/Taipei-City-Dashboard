package tools

import (
	"TaipeiCityDashboardBE/app/models"
	"context"
	"fmt"
	"strings"
	"time"
)

type YouBikeRealtimeArgs struct {
	City  string `json:"city"`  // "taipei" | "new_taipei"
	Mode  string `json:"mode"`  // "borrow" | "return"
	Limit int    `json:"limit"` // default 5
}

func QueryYouBikeRealtime(ctx context.Context, args string) (string, error) {
	var params YouBikeRealtimeArgs
	if err := parseArgs(args, &params); err != nil {
		return "", fmt.Errorf("invalid arguments: %v", err)
	}
	if params.Limit <= 0 {
		params.Limit = 5
	}
	if params.Mode == "" {
		params.Mode = "borrow"
	}

	tableName := "tran_ubike_realtime"
	cityName := "台北市"
	if params.City == "new_taipei" {
		tableName = "tran_ubike_realtime_new_tpe"
		cityName = "新北市"
	}

	type StationRow struct {
		StationID        string    `gorm:"column:station_id"`
		AvailRentGeneral int       `gorm:"column:available_rent_general_bikes"`
		AvailRentElectric int      `gorm:"column:available_rent_electric_bikes"`
		AvailReturn      int       `gorm:"column:available_return_bikes"`
		DataTime         time.Time `gorm:"column:data_time"`
	}

	var orderCol, whereClause string
	if params.Mode == "return" {
		orderCol = "available_return_bikes"
		whereClause = "available_return_bikes > 0"
	} else {
		orderCol = "available_rent_general_bikes"
		whereClause = "available_rent_general_bikes > 0"
	}

	var rows []StationRow
	err := models.DBDashboard.Table(tableName).
		Select("station_id, available_rent_general_bikes, available_rent_electric_bikes, available_return_bikes, data_time").
		Where(whereClause).
		Order(orderCol + " DESC").
		Limit(params.Limit).
		Find(&rows).Error
	if err != nil {
		return "", fmt.Errorf("查詢 YouBike 即時資料失敗: %v", err)
	}

	var totalCount, availCount int64
	models.DBDashboard.Table(tableName).Count(&totalCount)
	models.DBDashboard.Table(tableName).Where(whereClause).Count(&availCount)

	if len(rows) == 0 {
		label := "可借"
		if params.Mode == "return" {
			label = "可還"
		}
		return fmt.Sprintf("【%s YouBike 即時資料】\n目前查無%s的站點。", cityName, label), nil
	}

	dataTime := rows[0].DataTime.Format("2006-01-02 15:04")
	var sb strings.Builder
	if params.Mode == "return" {
		fmt.Fprintf(&sb, "【%s YouBike 即時可還空位 - 前%d名】\n資料時間：%s\n", cityName, len(rows), dataTime)
	} else {
		fmt.Fprintf(&sb, "【%s YouBike 即時可借車情況 - 前%d名】\n資料時間：%s\n", cityName, len(rows), dataTime)
	}
	for i, r := range rows {
		fmt.Fprintf(&sb, "%d. 站點 %s ─ 可借一般車：%d 輛 / 電輔車：%d 輛 / 可還空位：%d 格\n",
			i+1, r.StationID, r.AvailRentGeneral, r.AvailRentElectric, r.AvailReturn)
	}

	if params.Mode == "return" {
		fmt.Fprintf(&sb, "整體統計：共 %d 站中，有 %d 站有空位可還", totalCount, availCount)
	} else {
		fmt.Fprintf(&sb, "整體統計：共 %d 站中，有 %d 站有車可借", totalCount, availCount)
	}
	return sb.String(), nil
}

type YouBikePeakArgs struct {
	City  string `json:"city"`  // "taipei" | "new_taipei" | "all"
	Area  string `json:"area"`  // 行政區，空字串=不限
	Role  string `json:"role"`  // "all" | "借車壓力站" | "還車壓力站" | "均衡站"
	Limit int    `json:"limit"` // default 5
}

func QueryYouBikePeakAnalysis(ctx context.Context, args string) (string, error) {
	var params YouBikePeakArgs
	if err := parseArgs(args, &params); err != nil {
		return "", fmt.Errorf("invalid arguments: %v", err)
	}
	if params.Limit <= 0 {
		params.Limit = 5
	}
	if params.City == "" {
		params.City = "all"
	}
	if params.Role == "" {
		params.Role = "all"
	}

	cityMap := map[string]string{
		"taipei":     "TPE",
		"new_taipei": "NTPC",
	}

	type PeakRow struct {
		StationName   string  `gorm:"column:station_name"`
		City          string  `gorm:"column:city"`
		Area          string  `gorm:"column:area"`
		Role          string  `gorm:"column:role"`
		AvgBikeRate   float64 `gorm:"column:avg_bike_rate"`
		ZeroBikeRate  float64 `gorm:"column:zero_bike_rate"`
		ImbalanceRate float64 `gorm:"column:imbalance_rate"`
		Capacity      int     `gorm:"column:capacity"`
	}

	query := models.DBDashboard.Table("youbike_peak_station_metrics").
		Select("station_name, city, area, role, avg_bike_rate, zero_bike_rate, imbalance_rate, capacity")

	if cityLabel, ok := cityMap[params.City]; ok {
		query = query.Where("city = ?", cityLabel)
	}
	if params.Area != "" {
		query = query.Where("area = ?", params.Area)
	}
	if params.Role != "all" {
		query = query.Where("role = ?", params.Role)
	}

	var rows []PeakRow
	err := query.Order("imbalance_rate DESC").Limit(params.Limit).Find(&rows).Error
	if err != nil {
		return "", fmt.Errorf("查詢 YouBike 尖峰分析失敗: %v", err)
	}
	if len(rows) == 0 {
		return "查無符合條件的 YouBike 站點尖峰資料。", nil
	}

	titleCity := "大台北地區"
	if v, ok := cityMap[params.City]; ok {
		titleCity = v
	}
	titleRole := "高度失衡"
	if params.Role != "all" {
		titleRole = params.Role
	}
	if params.Area != "" {
		titleCity = params.Area + "（" + titleCity + "）"
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "【%s YouBike %s站點 - 前%d名】\n", titleCity, titleRole, len(rows))
	for i, r := range rows {
		fmt.Fprintf(&sb, "%d. %s ─ 角色：%s / 容量：%d 格\n   平均在車率：%d%% / 無車時間佔比：%d%% / 失衡率：%d%%\n",
			i+1, r.StationName, r.Role, r.Capacity,
			int(r.AvgBikeRate*100), int(r.ZeroBikeRate*100), int(r.ImbalanceRate*100))
	}
	return sb.String(), nil
}
