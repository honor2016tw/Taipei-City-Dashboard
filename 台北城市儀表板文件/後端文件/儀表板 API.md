# 儀表板 API

儀表板 API
=======

APIs [#](#apis)
---------------

### 獲取所有儀表板 [#](#獲取所有儀表板)

`GET` `/api/v1/dashboard`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` 只有公開儀表板   `User` `Admin` 公開和個人儀表板 |

**Response:**

```
content_paste{
    "data": {
        "public": [...], // 儀表板配置
        "personal": [...] // 儀表板配置
    },
    "status": "success"
}
```

### 透過 Index 獲取儀表板 [#](#透過-index-獲取儀表板)

`GET` `/api/v1/dashboard/:index`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` 只有公開儀表板   `User` `Admin` 公開和個人儀表板 |

**Response:**

```
content_paste{
    "data": [
        // 組成儀表板的組件配置
    ],
    "status": "success"
}
```

### 建立個人儀表板 [#](#建立個人儀表板)

`POST` `/api/v1/dashboard`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` `Admin` |

**Body:**

```
content_paste{
    // 儀表板配置參數，除 `index`（自動生成）
}
```

**Response:**

```
content_paste{
    "data": {
        // 新建立的儀表板配置
    },
    "status": "success"
}
```

### 建立公開儀表板 [#](#建立公開儀表板)

`GET` `/api/v1/dashboard/check-index/:index`

首先呼叫此 API 以檢查 Index 是否可用。

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Response:**

```
content_paste{
    "available": true,
    "status": "success"
}
```

`POST` `/api/v1/dashboard/public`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 儀表板配置參數（包括 Index）
}
```

**Response:**

```
content_paste{
    "data": {
        // 新建立的儀表板配置
    },
    "status": "success"
}
```

### 更新儀表板 [#](#更新儀表板)

`PATCH` `/api/v1/dashboard/:index`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` 只有個人儀表板   `Admin` 個人和公開儀表板 |

**Body:**

```
content_paste{
    // 要更新的儀表板配置參數。例如
    "name": "新名稱"
    // 不能更新 `index`
    // 上述參數應在資料庫中手動更新
}
```

**Response:**

```
content_paste{
    "data": {
        // 更新的儀表板配置
    },
    "status": "success"
}
```

### 刪除儀表板 [#](#刪除儀表板)

`DEL` `/api/v1/dashboard/:index`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` 只有個人儀表板   `Admin` 個人和公開儀表板 |

**Response:**

```
content_paste{
    "status": "success"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/dashboard-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 組件資料 API](/documentation/back-end/component-data-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 問題回報 API](/documentation/back-end/issue-apis)