# 貢獻者 API

貢獻者 API
=======

APIs [#](#apis)
---------------

### 建立貢獻者 [#](#建立貢獻者)

`POST` `/api/v1/contributor`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    "user_id": "Test",
    "user_name": "Test",
    "description": "Chu chu train",
    "identity": "Chu",
    "image": "https://...",
    "link": "https://...",
    "include": true
}
```

**Response:**

```
content_paste{
    "data": {
        "id": 96,
        "user_id": "Test",
        "user_name": "Test",
        "image": "https://...",
        "link": "https://...",
        "identity": "Chu",
        "description": "Chu chu train",
        "include": true,
        "created_at": "2024-06-13T05:40:34.355047911Z",
        "updated_at": "2024-06-13T05:40:34.355048025Z"
    },
    "status": "success"
}
```

### 獲取所有貢獻者 [#](#獲取所有貢獻者)

`GET` `/api/v1/contributor`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` |
| 查詢參數 | `pagesize` ---------------- 每頁的回報問題數量。 `pagenum` ------------------ 頁碼。需要 `pagesize`。 `sort` ----------------------- 用來排序的欄位。 `order` --------------------- "asc", "desc". |

**Response:**

```
content_paste{
    "data": [
        // 貢獻者
    ],
    "results": 1, // 回傳的貢獻者數量
    "status": "成功",
    "total": 1 // 貢獻者的總數量
}
```

### 更新貢獻者 [#](#更新貢獻者)

`PATCH` `/api/v1/contributor/:id`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 只有 id 欄位不能被更新
    ...
}
```

**Response:**

```
content_paste{
    // 更新後的貢獻者
}
```

### 刪除貢獻者 [#](#刪除貢獻者)

`DEL` `/api/v1/contributor/:id`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Response:**

```
content_paste{
    "status": "成功"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/contributor-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 問題回報 API](/documentation/back-end/issue-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 地圖視角 API](/documentation/back-end/viewpoint-apis)