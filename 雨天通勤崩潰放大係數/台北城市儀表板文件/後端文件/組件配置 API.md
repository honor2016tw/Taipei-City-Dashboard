# 組件配置 API

組件配置 API
========

APIs [#](#apis)
---------------

### 獲取所有組件 [#](#獲取所有組件)

`GET` `/component`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` |
| 查詢參數 | `pagesize` ------------- 每頁的組件數量。 `pagenum` --------------- 頁碼。需要 `pagesize`。 `searchbyname` ------ 透過組件名稱搜尋。 `searchbyindex` ---- 透過組件 Index 搜尋。  `filterby` ------------- 用來篩選的欄位。  `filtermode` --------- "eq", "ne", "gt", "lt", "in". `sort` -------------------- 用來排序的欄位。 `order` ------------------ "asc", "desc". `city` -------------------- "taipei", "metrotaipei". |

**Response:**

```
content_paste{
    "data": [
        {
            // 組件配置
        },...
    ],
    "results": 61, // 回傳的組件數量
    "status": "success",
    "total": 61 // 組件總數
}
```

### 透過 ID 獲取組件 [#](#透過-id-獲取組件)

`GET` `/component/:id`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` |

**Response:**

```
content_paste{
    "data": {
        // 組件配置
    },
    "status": "success"
}
```

### 更新組件配置 [#](#更新組件配置)

`PATCH` `/component/:id`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 更新的組件配置參數。例如
    "name": "New Name"
    // 不能更新 `id`, `index`, `map_config_ids`, `query_type`, `query_chart`, `query_history`
    // 上述參數應在資料庫中手動更新
}
```

**Response:**

```
content_paste{
    "data": {
        // 更新的組件配置
    },
    "status": "success"
}
```

### 更新圖表配置 [#](#更新圖表配置)

`PATCH` `/component/:id/chart`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 更新的圖表配置參數。例如
    "unit": "km"
    // 不能更新 `index`
    // 上述參數應在資料庫中手動更新
}
```

**Response:**

```
content_paste{
    "data": {
        // 更新的圖表配置
    },
    "status": "success"
}
```

### 更新地圖配置 [#](#更新地圖配置)

`PATCH` `/component/:id/map`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 更新的地圖配置參數。例如
    "type": "line"
    // 不能更新 `id`
    // 上述參數應在資料庫中手動更新
}
```

**Response:**

```
content_paste{
    "data": {
        // 更新的地圖配置
    },
    "status": "success"
}
```

### 刪除組件 [#](#刪除組件)

`DEL` `/component/:id`

> #### 警告 - 1
>
> 本 API 仍在 beta 中。前端目前未使用。

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Response:**

```
content_paste{
    "status": "success"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/component-config-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 用戶 API](/documentation/back-end/user-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 組件資料 API](/documentation/back-end/component-data-apis)