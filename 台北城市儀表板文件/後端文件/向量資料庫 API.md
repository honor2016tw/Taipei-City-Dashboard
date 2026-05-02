# 向量資料庫 API

向量資料庫 API
=========

向量資料庫 [#](#向量資料庫)
-----------------

查詢向量資料庫，輸入關鍵字，向量資料庫回傳，相似度高的內容。

APIs [#](#apis)
---------------

### 查詢組件 [#](#查詢組件)

`POST` `/api/v1/vector/component`

| 項目 | 描述 |
| --- | --- |
| 權限 | `Guest` |
| 查詢參數 | `query` ------------- 查詢字串 |

**Response:**

```
content_paste{
    "data": [
        {
            "id": 217,
            "index": "bike_map",
            "name": "自行車道路網圖資",
            "city": "taipei",
            "score": 0.8181
        },
        {
            "id": 213,
            "index": "bike_network",
            "name": "自行車道路統計資料",
            "city": "taipei",
            "score": 0.8158
        },
        {
            "id": 212,
            "index": "ebus_percent",
            "name": "電動巴士比例",
            "city": "taipei",
            "score": 0.814
        }
    ],
    "status": "success"
}
```

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/vectordb-apis.md)

[##### keyboard\_arrow\_left前一篇文章

###### 對話紀錄 API](/documentation/back-end/chatlog-apis)

[##### 下一篇文章keyboard\_arrow\_right

###### AI 對話 API](/documentation/back-end/ai-apis)