# 對話紀錄 API

對話紀錄 API
========

對話紀錄 [#](#對話紀錄)
---------------

紀錄使用者與 Chatbox 對話紀錄。

APIs [#](#apis)
---------------

### 建立對話紀錄 [#](#建立對話紀錄)

`POST` `/api/v1/chatlog`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |
| 查詢參數 | `session` ------------- sessionid。 `question` --------------- 問題。 `answer` ------ 回答。 |

**Response:**

```
content_paste{
    "data": {
        "id": 1,
        "session": "bike",
        "question": "show me bike components",
        "answer": "There are 5 bike components, 1 = .. 2= ..",
        "ip_address": "192.168.65.1",
        "created_at": "2026-01-27T07:31:40.07163905Z"
    },
    "status": "success"
}
```

### 取得所有對話紀錄 [#](#取得所有對話紀錄)

`GET` `/api/v1/chatlog/session/`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |

**Response:**

```
content_paste{
    "data": [
        {
            "session": "bike",
            "created_at": "2025-11-27T09:36:09.374536Z"
        },
        {
            "session": "bus",
            "created_at": "2025-11-27T09:36:09.374536Z"
        },
        {
            "session": "building",
            "created_at": "2025-11-27T09:36:09.374536Z"
        }
    ],
    "status": "success"
}
```

### 取得單一對話紀錄內容 [#](#取得單一對話紀錄內容)

`GET` `/api/v1/chatlog/session/:session`

| 項目 | 描述 |
| --- | --- |
| 權限 | `User` |
| 查詢參數 | `session` ------------- sessionid。 |

**Response:**

```
content_paste{
    "data": [
        {
            "id": 1,
            "session": "bike",
            "question": "Do you have bike components",
            "answer": "Yes. There are 5 bike components",
            "ip_address": "192.168.65.1",
            "created_at": "2026-01-27T07:31:40.07163905Z"
        },
        {
            "id": 2,
            "session": "bike",
            "question": "show me all the bike components",
            "answer": "components 1 = .. 2= ..",
            "ip_address": "192.168.65.1",
            "created_at": "2026-01-27T07:32:40.07163905Z"
        },
    ],
    "status": "success"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/chatlog-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 地圖視角 API](/documentation/back-end/viewpoint-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### 向量資料庫 API](/documentation/back-end/vectordb-apis)