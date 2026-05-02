# Go 後端

Go 後端
=====

[play\_circle

##### 後端客製化指南

###### BE Customization](https://www.youtube.com/watch?v=LRQ61aLv-S4)

全域服務 [#](#全域服務)
---------------

### Cobra [#](#cobra)

Cobra 指令儲存在 `/cmd/root.go`。如果啟動應用程式時未指定執行指令，應用程式會執行 `TaipeiCityDashboardBE` 指令。本專案亦包含其他指令如 `migrateDB`等。

### Logs [#](#logs)

Logs 的相關設定儲存在 `/logs/logs.go`，為應用程式提供全域 logging。

### 全域變量 (global variables) [#](#全域變量-(global-variables))

全域變量儲存在 `/global/consts.go` 和 `/global/vars.go`。前者包含應用程式中使用的所有常量，而後者讀取並儲存專案的環境變量。

App [#](#app)
-------------

主應用程式儲存在 `/app/app.go`。它包含一個 `StartApplication` 函式，用來初始化應用程式並啟動伺服器。在 `/app` 中，還有六個額外的資料夾，包含應用程式的 router 、 middleware 、 controller 、 資料庫 handler、暫存 handler 和 utility 函式。

### Router [#](#router)

Router 儲存在 `/app/router/router.go`。它包含應用程式的所有路徑。在[下下章](/documentation/back-end/authentication-apis)將提供有關此應用程式中可用路徑的更多資訊。

### Middlewares [#](#middlewares)

Middleware 儲存在 `/app/middlewares`。這些 middleware 控制 API 呼叫頻率、身份驗證、權限管理等。

### Controllers [#](#controllers)

Controller 儲存在 `/app/controllers`。這些 controller 處理身份驗證和應用程式的運行邏輯。在[下一章之後](/documentation/back-end/authentication-apis)將提供有關此應用程式中可用 controller 的更多資訊。

### 資料庫 (Database) [#](#資料庫-(database))

連接到 PostgreSQL 資料庫的主要邏輯儲存在 `/app/models/database.go`。資料庫的連線透過 `DBDashboard`（與 `dashboard` 資料庫的連線）和 `DBManager`（與 `dashboardmanager` 資料庫的連線）變量在應用程式全域中均可使用。

資料庫的 model 和 handler 儲存在 `/app/models`，檔名與使用它們的 controller 檔名相同。例如，`/models/dashboard.go` 檔案包含由 `/controllers/dashboard.go` 中的 controller 使用的 `Dashboard` 模型。

### 暫存 (Cache) [#](#暫存-(cache))

連接到 Redis cache 的主要邏輯儲存在 `/app/cache/redis.go`。連線透過 `Redis` 變量在應用程式全域中均可使用。

### Utilities [#](#utilities)

Utility 函式儲存在 `/app/utils`。這些函式在 middleware 、 controller 和資料庫 handler 中使用。

> #### 資訊 - 1
>
> 當建立新函式時，請將其歸類在 `/app` 中相對應的資料夾中。
>
> 處理 request 並將其傳遞給 controller 的函式，請將其放在 `/app/middlewares` 資料夾中；處理 request 並回應給客戶端的函式，請將其放在 `/app/controllers` 資料夾中；與資料庫溝通的函式，請將其放在 `/app/models` 資料夾中；不屬於上述類別的函式，請將其放在 `/app/utils` 資料夾中。

[auto\_fix\_high於Github編輯此文章](https://github.com/taipei-doit/Taipei-City-Dashboard-Documentation/edit/main/src/assets/articles/back-end-ch/go-backend.md)

[##### keyboard\_arrow\_left前一篇文章

###### 資料庫概覽](/documentation/back-end/database-overview)

[##### 下一篇文章keyboard\_arrow\_right

###### 用戶、權限、群組資料庫](/documentation/back-end/users-roles-groups-db)