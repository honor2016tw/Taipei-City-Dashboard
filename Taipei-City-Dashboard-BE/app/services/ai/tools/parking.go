package tools

import (
	"TaipeiCityDashboardBE/app/models"
	"context"
	"fmt"
	"strings"
	"time"
)

type ParkingAvailabilityArgs struct {
	City     string `json:"city"`     // "taipei" | "new_taipei"
	District string `json:"district"` // e.g., "信義區"，空字串=不限
	Limit    int    `json:"limit"`    // default 5
}

type parkingRow struct {
	Name         string    `gorm:"column:name"`
	Dist         string    `gorm:"column:dist"`
	Address      string    `gorm:"column:address"`
	TotalCar     int       `gorm:"column:total_car"`
	AvailableCar int       `gorm:"column:available_car"`
	AvailPct     int       `gorm:"column:available_pct"`
	DataTime     time.Time `gorm:"column:imported_at"`
}

func QueryParkingAvailability(ctx context.Context, args string) (string, error) {
	var params ParkingAvailabilityArgs
	if err := parseArgs(args, &params); err != nil {
		return "", fmt.Errorf("invalid arguments: %v", err)
	}
	if params.Limit <= 0 {
		params.Limit = 5
	}

	// tran_parking.city uses TPE/NTPC
	cityCode := "TPE"
	cityName := "台北市"
	if params.City == "new_taipei" {
		cityCode = "NTPC"
		cityName = "新北市"
	}

	var rows []parkingRow
	query := `
		SELECT p.name, p.dist, p.address, p.total_car, r.available_car,
		       ROUND(r.available_car::numeric / NULLIF(p.total_car, 0) * 100)::int AS available_pct,
		       r.imported_at
		FROM tran_parking p
		JOIN tran_parking_capacity_realtime r ON p.station_id = r.station_id
		WHERE p.city = ?
		  AND (? = '' OR p.dist = ?)
		  AND r.available_car > 0
		ORDER BY r.available_car DESC
		LIMIT ?`

	err := models.DBDashboard.Raw(query, cityCode, params.District, params.District, params.Limit).
		Scan(&rows).Error
	if err != nil {
		return "", fmt.Errorf("查詢停車場即時車位失敗: %v", err)
	}

	// Summary counts
	var totalInScope, availInScope int64
	countQuery := `
		SELECT COUNT(*) FROM tran_parking p
		JOIN tran_parking_capacity_realtime r ON p.station_id = r.station_id
		WHERE p.city = ? AND (? = '' OR p.dist = ?)`
	models.DBDashboard.Raw(countQuery+" AND r.available_car > 0", cityCode, params.District, params.District).
		Scan(&availInScope)
	models.DBDashboard.Raw(countQuery, cityCode, params.District, params.District).
		Scan(&totalInScope)

	if len(rows) == 0 {
		scope := cityName
		if params.District != "" {
			scope = params.District
		}
		return fmt.Sprintf("【%s停車場即時車位】\n目前查無有剩餘車位的停車場。", scope), nil
	}

	dataTime := rows[0].DataTime.Format("2006-01-02 15:04")
	scope := cityName
	if params.District != "" {
		scope = params.District
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "【%s停車場即時車位 - 前%d名】\n資料時間：%s\n", scope, len(rows), dataTime)
	for i, r := range rows {
		fmt.Fprintf(&sb, "%d. %s ─ 剩餘：%d / 總容量：%d（%d%%）\n   地址：%s\n",
			i+1, r.Name, r.AvailableCar, r.TotalCar, r.AvailPct, r.Address)
	}
	fmt.Fprintf(&sb, "整體：%s共 %d 座停車場，目前 %d 座有剩餘車位", scope, totalInScope, availInScope)
	return sb.String(), nil
}
