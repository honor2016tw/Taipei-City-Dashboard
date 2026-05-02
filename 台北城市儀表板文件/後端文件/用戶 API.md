# 用戶 API

用戶 API
======

APIs [#](#apis)
---------------

### 獲取目前用戶資訊 [#](#獲取目前用戶資訊)

`GET` `/api/v1/user/me`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Response:**

```
content_paste{
    "status": "success",
    "user": {
        "user_id": 1,
        "name": "Igor Ho",
        "account": "tuic@gov.taipei",
        "TpAccount": null,
        "is_admin": true,
        "is_active": true,
        "is_whitelist": true,
        "is_blacked": false,
        "expired_at": "2024-03-04T09:01:31.001728Z",
        "created_at": "2024-02-19T02:31:34.727546Z",
        "login_at": "2024-03-05T03:06:59.372152Z"
    }
}
```

### 更新目前用戶資訊 [#](#更新目前用戶資訊)

`PATCH` `/api/v1/user/me`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Body:**

```
content_paste{
    // 只有名稱可以更新
    "name": "Igor"
}
```

**Response:**

```
content_paste{
    "data": {
        "name": "Igor"
    },
    "status": "success"
}
```

### 獲取所有用戶 [#](#獲取所有用戶)

`GET` `/api/v1/user`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |
| 查詢參數 | `pagesize` ---------------- 每頁的用戶數量。 `pagenum` ------------------ 頁碼。`pagesize`需填寫。 `sort` ----------------------- 用來排序的欄位。 `order` --------------------- "asc", "desc". `searchbyname` --------- 透過用戶名稱搜尋。 `searchbyid`------------- 透過 user\_id 搜尋。 |

**Response:**

```
content_paste{
    "data": [
        // Users
    ],
    "results": 1, // 回傳的用戶數量
    "status": "success",
    "total": 1 // 用戶總數
}
```

### 編輯用戶資訊 (管理員) [#](#編輯用戶資訊-(管理員))

`PATCH` `/api/v1/user/:id`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Admin` |

**Body:**

```
content_paste{
    // 只有以下參數可以更新
    "name": "Igor H",
    "is_admin": true,
    "is_active": true,
    "is_whitelist": true,
    "is_blacked": false
}
```

**Response:**

```
content_paste{
    "status": "success",
    "user": {
        "name": "Igor H",
        "is_admin": true,
        "is_active": true,
        "is_whitelist": true,
        "is_blacked": false,
        "expired_at": "0001-01-01T00:00:00Z" // 如果 is_active 為 false，由應用程式自動填入
    }
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/user-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 用戶驗證 API](/documentation/back-end/authentication-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 組件配置 API](/documentation/back-end/component-config-apis)