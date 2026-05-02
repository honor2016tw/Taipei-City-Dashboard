package tools

import (
	"TaipeiCityDashboardBE/app/models"
	"context"
	"fmt"
	"strings"
)

type MetroLastMileArgs struct {
	City         string `json:"city"`          // "taipei" | "new_taipei" | "all"
	StatusFilter string `json:"status_filter"` // "all" | "good" | "watch" | "alert"
	SortBy       string `json:"sort_by"`       // "risk" | "service"
	Limit        int    `json:"limit"`         // default 5
}

func QueryMetroLastMile(ctx context.Context, args string) (string, error) {
	var params MetroLastMileArgs
	if err := parseArgs(args, &params); err != nil {
		return "", fmt.Errorf("invalid arguments: %v", err)
	}
	if params.Limit <= 0 {
		params.Limit = 5
	}
	if params.City == "" {
		params.City = "all"
	}
	if params.StatusFilter == "" {
		params.StatusFilter = "all"
	}
	if params.SortBy == "" {
		params.SortBy = "risk"
	}

	// metro_last_mile_service_health.city uses 台北/新北
	cityMap := map[string]string{
		"taipei":    "台北",
		"new_taipei": "新北",
	}

	type MetroRow struct {
		StationName       string  `gorm:"column:station_name"`
		City              string  `gorm:"column:city"`
		ServiceStatus     string  `gorm:"column:service_status"`
		StatusLabel       string  `gorm:"column:status_label"`
		ServiceScore      float64 `gorm:"column:service_score"`
		RiskScore         float64 `gorm:"column:risk_score"`
		AvailRentBikes    int     `gorm:"column:available_rent_bikes"`
		AvailReturnBikes  int     `gorm:"column:available_return_bikes"`
		BusStopCount      int     `gorm:"column:bus_stop_count"`
		MedianEtaMin      float64 `gorm:"column:median_eta_min"`
	}

	query := models.DBDashboard.Table("metro_last_mile_service_health").
		Select("station_name, city, service_status, status_label, service_score, risk_score, available_rent_bikes, available_return_bikes, bus_stop_count, median_eta_min")

	if cityLabel, ok := cityMap[params.City]; ok {
		query = query.Where("city = ?", cityLabel)
	}
	if params.StatusFilter != "all" {
		query = query.Where("service_status = ?", params.StatusFilter)
	}

	if params.SortBy == "service" {
		query = query.Order("service_score DESC")
	} else {
		query = query.Order("risk_score DESC")
	}

	var rows []MetroRow
	err := query.Limit(params.Limit).Find(&rows).Error
	if err != nil {
		return "", fmt.Errorf("查詢捷運最後一哩路資料失敗: %v", err)
	}
	if len(rows) == 0 {
		return "查無符合條件的捷運站最後一哩路資料。", nil
	}

	titleScope := "大台北地區"
	if v, ok := cityMap[params.City]; ok {
		titleScope = v
	}

	var titleSort string
	if params.SortBy == "service" {
		titleSort = "服務最穩定"
	} else {
		titleSort = "最需改善"
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "【%s最後一哩路%s的捷運站 - 前%d名】\n", titleScope, titleSort, len(rows))
	for i, r := range rows {
		statusLabel := r.StatusLabel
		if statusLabel == "" {
			statusLabel = r.ServiceStatus
		}
		fmt.Fprintf(&sb, "%d. %s（%s）- 狀態：%s ─ 服務分 %.0f / 風險分 %.0f\n   YouBike：可借 %d 輛 / 公車站：%d 個 / 中位等車時間：%.1f 分鐘\n",
			i+1, r.StationName, r.City,
			statusLabel,
			r.ServiceScore, r.RiskScore,
			r.AvailRentBikes, r.BusStopCount, r.MedianEtaMin)
	}
	return sb.String(), nil
}
