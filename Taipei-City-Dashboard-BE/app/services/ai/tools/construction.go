package tools

import (
	"TaipeiCityDashboardBE/app/models"
	"context"
	"fmt"
	"strings"
	"time"
)

type ConstructionWorksArgs struct {
	City     string `json:"city"`     // "taipei" | "new_taipei" | "all"
	District string `json:"district"` // e.g., "大安區"，空字串=不限
	Limit    int    `json:"limit"`    // default 10
}

func QueryConstructionWorks(ctx context.Context, args string) (string, error) {
	var params ConstructionWorksArgs
	if err := parseArgs(args, &params); err != nil {
		return "", fmt.Errorf("invalid arguments: %v", err)
	}
	if params.Limit <= 0 {
		params.Limit = 10
	}
	if params.City == "" {
		params.City = "all"
	}

	// source_city column contains Chinese city names
	cityKeywordMap := map[string]string{
		"taipei":    "台北",
		"new_taipei": "新北",
	}

	type WorkRow struct {
		ProjectName string    `gorm:"column:project_name"`
		District    string    `gorm:"column:district"`
		Address     string    `gorm:"column:address"`
		StartDate   time.Time `gorm:"column:start_date"`
		EndDate     time.Time `gorm:"column:end_date"`
		SourceCity  string    `gorm:"column:source_city"`
	}

	query := models.DBDashboard.Table("traffic_todayworks_metrotaipei").
		Select("project_name, district, address, start_date, end_date, source_city").
		Where("is_expired = false")

	if keyword, ok := cityKeywordMap[params.City]; ok {
		query = query.Where("source_city LIKE ?", "%"+keyword+"%")
	}
	if params.District != "" {
		query = query.Where("district = ?", params.District)
	}

	var rows []WorkRow
	err := query.Order("end_date ASC").Limit(params.Limit).Find(&rows).Error
	if err != nil {
		return "", fmt.Errorf("查詢施工資料失敗: %v", err)
	}

	// Total count for context
	var totalCount int64
	countQ := models.DBDashboard.Table("traffic_todayworks_metrotaipei").Where("is_expired = false")
	if keyword, ok := cityKeywordMap[params.City]; ok {
		countQ = countQ.Where("source_city LIKE ?", "%"+keyword+"%")
	}
	if params.District != "" {
		countQ = countQ.Where("district = ?", params.District)
	}
	countQ.Count(&totalCount)

	scope := "大台北地區"
	if params.City == "taipei" {
		scope = "台北市"
	} else if params.City == "new_taipei" {
		scope = "新北市"
	}
	if params.District != "" {
		scope = params.District
	}

	if len(rows) == 0 {
		return fmt.Sprintf("【%s目前進行中施工】\n目前查無進行中的施工項目。", scope), nil
	}

	var sb strings.Builder
	fmt.Fprintf(&sb, "【%s目前進行中施工 - 共 %d 件（顯示前 %d 件）】\n", scope, totalCount, len(rows))
	for i, r := range rows {
		fmt.Fprintf(&sb, "%d. %s\n   地址：%s %s\n   工期：%s ～ %s\n",
			i+1, r.ProjectName,
			r.District, r.Address,
			r.StartDate.Format("2006-01-02"),
			r.EndDate.Format("2006-01-02"))
	}
	return sb.String(), nil
}
