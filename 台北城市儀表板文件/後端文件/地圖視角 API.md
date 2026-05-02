# 地圖視角 API

地圖視角 API
========

APIs [#](#apis)
---------------

### 為使用者建立地圖視角/圖標 [#](#為使用者建立地圖視角/圖標)

`POST` `/api/v1/user/:userid/viewpoint`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Body:**

```
content_paste{
    "bearing": -56.75256000000002,
    "center_x": 121.51684,
    "center_y": 25.049266999999972,
    "name": "Test",
    "pitch": 70.56765000000001,
    "point_type": "view",
    "zoom": 12.036047,
}
```

**Response:**

```
content_paste{
    "data": {
        "id": 19,
        "user_id": 24,
        "center_x": 121.51684,
        "center_y": 25.049267,
        "zoom": 12.036047,
        "pitch": 70.56765,
        "bearing": -56.75256,
        "name": "Test",
        "point_type": "view",
    },
    "status": "success"
}
```

### 取得使用者的所有地圖視角 [#](#取得使用者的所有地圖視角)

`GET` `/api/v1/user/:userid/viewpoint`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Response:**

```
content_paste{
    "data": [
        // 地圖視角
    ],
    "results": 1, // 回傳的地圖視角數量
    "status": "success",
    "total": 1 // 地圖視角總數量
}
```

### 刪除使用者的地圖視角 [#](#刪除使用者的地圖視角)

`DEL` `/api/v1/user/:userid/viewpoint/:viewpointid`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Response:**

```
content_paste{
    "status": "success"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/viewpoint-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 貢獻者 API](/documentation/back-end/contributor-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 對話紀錄 API](/documentation/back-end/chatlog-apis)