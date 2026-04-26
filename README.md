# 📦 本地部署指南 (Local Deployment Guide)

本文件說明如何在本地環境完整部署 **臺北城市儀表板 (Taipei City Dashboard)** 服務。

---

## 目錄

- [系統架構概覽](#系統架構概覽)
- [前置需求](#前置需求)
- [快速部署（TL;DR）](#快速部署tldr)
- [詳細步驟](#詳細步驟)
  - [Step 1：設定環境變數](#step-1設定環境變數)
  - [Step 2：建立 Docker 網路](#step-2建立-docker-網路)
  - [Step 3：啟動資料庫服務](#step-3啟動資料庫服務)
  - [Step 4：初始化（安裝依賴 & 資料庫 Migration）](#step-4初始化安裝依賴--資料庫-migration)
  - [Step 5：Build 後端 Docker Image](#step-5build-後端-docker-image)
  - [Step 6：啟動前端與後端服務](#step-6啟動前端與後端服務)
- [服務存取方式](#服務存取方式)
- [Port 衝突排除](#port-衝突排除)
- [常用維運指令](#常用維運指令)
- [完整清除（重新來過）](#完整清除重新來過)
- [常見問題 FAQ](#常見問題-faq)

---

## 系統架構概覽

```
┌──────────────────────────────────────────────────────────┐
│                     Docker Network: br_dashboard         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Nginx   │  │ Frontend │  │ Backend  │  │  Redis   │ │
│  │  :80/443 │  │ (Vite)   │  │ (Go/Gin) │  │  :6379   │ │
│  │          │──│  :8080   │  │  :8088   │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ postgres-data │  │postgres-manager│  │   Qdrant     │ │
│  │ (Dashboard DB)│  │ (Manager DB)  │  │  :6333/6334  │ │
│  │    :5432      │  │    :5432      │  │              │ │
│  └───────────────┘  └───────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────┐                                            │
│  │ pgAdmin  │                                            │
│  │  :8889   │                                            │
│  └──────────┘                                            │
└──────────────────────────────────────────────────────────┘
```

| 服務 | 技術 | 說明 |
|------|------|------|
| **Frontend** | Vue 3 + Vite | 儀表板前端 UI |
| **Backend** | Go (Gin) | RESTful API Server |
| **postgres-data** | PostGIS 16 | 儀表板資料儲存 |
| **postgres-manager** | PostGIS 16 | 後台管理資料儲存 |
| **Redis** | Redis 7.2 | 快取 |
| **Qdrant** | Qdrant (latest) | 向量資料庫（AI 搜尋用） |
| **pgAdmin** | pgAdmin 4 | 資料庫管理 Web UI |
| **Nginx** | Nginx | 反向代理（本地開發可選） |

---

## 前置需求

在開始之前，請確認你的環境已安裝以下工具：

| 工具 | 最低版本 | 安裝方式 |
|------|----------|----------|
| **Docker Desktop** | 4.x+ | [下載頁面](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | v2.x+ | 包含在 Docker Desktop 中 |
| **Git** | 任意 | `brew install git` (macOS) |

> **💡 確認安裝：**
> ```bash
> docker --version          # Docker version 28.x.x
> docker compose version    # Docker Compose version v2.x.x
> ```

> **⚠️ 重要：** 啟動部署前，請確認 **Docker Desktop 已開啟且正在運行**。
> ```bash
> # macOS 開啟 Docker Desktop
> open -a Docker
>
> # 確認 Docker daemon 已就緒
> docker info > /dev/null 2>&1 && echo "✅ Docker is ready" || echo "❌ Docker is not running"
> ```

---

## 快速部署（TL;DR）

如果你只是想快速跑起來，可以依序執行以下指令：

```bash
# 1. 進入 docker 目錄
cd docker

# 2. 從 template 建立 .env 並填入開發用密碼
cp .env.template .env
# 編輯 .env，至少填入以下欄位（參考 Step 1）

# 3. 建立 Docker 網路
docker network create --driver=bridge \
  --subnet=192.168.128.0/24 \
  --gateway=192.168.128.1 \
  br_dashboard

# 4. 啟動資料庫
docker compose -f docker-compose-db.yaml up -d

# 5. 等待資料庫就緒（約 5-10 秒）
sleep 10

# 6. 初始化：安裝前端依賴
docker compose -f docker-compose-init.yaml run --rm dashboard-fe-init

# 7. 初始化：Manager DB Migration + 建立管理員帳號
docker compose -f docker-compose-init.yaml run --rm dashboard-be-init-manager

# 8. 初始化：匯入 Dashboard 範例資料
docker compose -f docker-compose-init.yaml run --rm dashboard-be-init-dashboard

# 9. Build 後端 Image（含 ONNX Model，首次約 5-10 分鐘）
docker build --target dev -t dashboard-be-dev:latest ../Taipei-City-Dashboard-BE/

# 10. 啟動前端 + 後端
docker compose -f docker-compose.yaml up -d dashboard-fe dashboard-be

# 🎉 完成！前端：http://localhost:8080 | 後端 API：http://localhost:8088
```

---

## 詳細步驟

### Step 1：設定環境變數

所有 Docker Compose 都會從 `docker/.env` 讀取環境變數。此檔案已被 `.gitignore` 排除，不會被提交到 Git。

```bash
cd docker
cp .env.template .env
```

用你喜歡的編輯器開啟 `.env`，**至少填入以下必填欄位**：

```dotenv
## 資料庫密碼（必填，可自訂）
DB_DASHBOARD_PASSWORD=postgres
DB_MANAGER_PASSWORD=postgres

## 預設管理員帳號（必填，用於首次登入）
DASHBOARD_DEFAULT_USERNAME=admin
DASHBOARD_DEFAULT_Email=admin@example.com
DASHBOARD_DEFAULT_PASSWORD=admin123

## pgAdmin 登入（必填）
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin
```

其他欄位說明：

| 欄位 | 預設值 | 說明 |
|------|--------|------|
| `VITE_API_URL` | `/api/dev` | 前端 API 路徑，本地開發不需改 |
| `NODE_ENV` | `development` | 前端環境模式 |
| `GIN_MODE` | `debug` | 後端 Gin 模式 (debug/release/test) |
| `GIN_DOMAIN` | `0.0.0.0` | 後端監聽位址，開發用 0.0.0.0 |
| `VITE_MAPBOXTOKEN` | (空) | Mapbox Token（地圖功能需要，可先不填） |
| `QDRANT_API_KEY` | `your_api_key` | Qdrant API Key（開發環境可用預設值） |
| `TWCC_API_KEY` | `your_twcc_api_key_here` | TWCC AI API Key（AI Chat 功能需要） |
| 標記為 `[External Dev Don't Need to Fill]` 的欄位 | (空) | 外部開發者不需填寫，留空即可 |

---

### Step 2：建立 Docker 網路

所有容器都運行在同一個自訂 bridge 網路 `br_dashboard` 中，讓容器間可以透過容器名稱互相通訊。

```bash
docker network create --driver=bridge \
  --subnet=192.168.128.0/24 \
  --gateway=192.168.128.1 \
  br_dashboard
```

> **💡 提示：** 如果網路已存在，會出現錯誤訊息 `network with name br_dashboard already exists`，這是正常的，可忽略。

驗證網路已建立：
```bash
docker network ls | grep br_dashboard
```

---

### Step 3：啟動資料庫服務

先啟動所有基礎設施服務（PostgreSQL × 2、Redis、Qdrant、pgAdmin）：

```bash
cd docker
docker compose -f docker-compose-db.yaml up -d
```

這會啟動以下 5 個容器：

| 容器 | Image | 對外 Port |
|------|-------|-----------|
| `postgres-data` | postgis/postgis:16-3.4-alpine | (無，僅內部) |
| `postgres-manager` | postgis/postgis:16-3.4-alpine | 5432 |
| `redis` | redis:7.2.3-alpine | (無，僅內部) |
| `qdrant` | qdrant/qdrant:latest | 6333, 6334 |
| `pgadmin` | dpage/pgadmin4:latest | 8889 |

等待資料庫完全啟動：

```bash
# 等待 postgres-data 就緒
docker exec postgres-data pg_isready -U postgres
# 應看到：accepting connections

# 等待 postgres-manager 就緒
docker exec postgres-manager pg_isready -U postgres
# 應看到：accepting connections
```

> **⚠️ Port 5432 衝突？** 如果你本機已有 PostgreSQL 佔用 5432，請參考 [Port 衝突排除](#port-衝突排除) 章節。

---

### Step 4：初始化（安裝依賴 & 資料庫 Migration）

此步驟會透過一次性容器完成三件事：

#### 4-1. 安裝前端 Node.js 依賴

```bash
docker compose -f docker-compose-init.yaml run --rm dashboard-fe-init
```

這相當於在容器中執行 `npm ci`，會將 `node_modules` 安裝到 `Taipei-City-Dashboard-FE/` 目錄下。

#### 4-2. Manager DB — Schema Migration + 建立管理員帳號

```bash
docker compose -f docker-compose-init.yaml run --rm dashboard-be-init-manager
```

這會：
- 建立 Manager DB 的所有資料表
- 匯入 `db-sample-data/dashboardmanager-demo.sql` 範例資料
- 使用 `.env` 中的 `DASHBOARD_DEFAULT_USERNAME` / `DASHBOARD_DEFAULT_PASSWORD` 建立管理員帳號

#### 4-3. Dashboard DB — 匯入儀表板範例資料

```bash
docker compose -f docker-compose-init.yaml run --rm dashboard-be-init-dashboard
```

這會匯入 `db-sample-data/dashboard-demo.sql` 的範例儀表板資料（約 2.4MB）。

> **💡 成功標誌：** 每個指令結束時應看到類似以下日誌：
> ```
> [info] import file name: /opt/db-sample-data/dashboard-demo.sql
> [info] DASHBOARD database connection closed
> ```

---

### Step 5：Build 後端 Docker Image

後端使用自訂 Docker Image `dashboard-be-dev:latest`，其中包含：
- Go 1.25.4 runtime
- ONNX Runtime（用於 AI embedding 模型）
- 預先匯出的 E5 文字嵌入模型

```bash
docker build --target dev -t dashboard-be-dev:latest ../Taipei-City-Dashboard-BE/
```

> **⏱ 首次 build 約需 5-10 分鐘**（需下載 Python 套件 + 匯出 ONNX 模型 + Go 基底映像）。
> 後續 rebuild 會利用 Docker cache，速度快很多。

驗證 Image 已建立：
```bash
docker images | grep dashboard-be-dev
```

---

### Step 6：啟動前端與後端服務

```bash
docker compose -f docker-compose.yaml up -d dashboard-fe dashboard-be
```

驗證服務是否正常：

```bash
# 查看所有容器狀態
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 查看前端 log（應看到 VITE ready）
docker logs dashboard-fe

# 查看後端 log（應看到 GIN-debug 路由列表）
docker logs dashboard-be
```

前端正常啟動日誌：
```
VITE v5.2.9  ready in 257 ms

  ➜  Local:   http://localhost:80/
  ➜  Network: http://192.168.128.x:80/
```

後端正常啟動日誌：
```
[GIN-debug] GET /api/v1/component/ --> ...
[GIN-debug] POST /api/v1/ai/chat/twai --> ...
[info] 0.0.0.0:8080
```

---

## 服務存取方式

部署完成後，可透過以下位址存取各服務：

| 服務 | URL | 說明 |
|------|-----|------|
| 🖥️ **儀表板前端** | http://localhost:8080 | 主要使用入口 |
| ⚡ **後端 API** | http://localhost:8088/api/v1/ | RESTful API |
| 🗄️ **pgAdmin** | http://localhost:8889 | 資料庫管理介面 |
| 🔍 **Qdrant Dashboard** | http://localhost:6333/dashboard | 向量資料庫管理 |

### 登入資訊

| 服務 | 帳號 | 密碼 |
|------|------|------|
| **儀表板** | `.env` 中的 `DASHBOARD_DEFAULT_USERNAME` | `.env` 中的 `DASHBOARD_DEFAULT_PASSWORD` |
| **pgAdmin** | `.env` 中的 `PGADMIN_DEFAULT_EMAIL` | `.env` 中的 `PGADMIN_DEFAULT_PASSWORD` |

### 在 pgAdmin 中連線資料庫

新增 Server 時使用以下設定：

| 參數 | Dashboard DB | Manager DB |
|------|-------------|------------|
| Host | `postgres-data` | `postgres-manager` |
| Port | `5432` | `5432` |
| Database | `dashboard` | `dashboardmanager` |
| Username | `postgres` | `postgres` |
| Password | `.env` 中設定的密碼 | `.env` 中設定的密碼 |

> **💡 注意：** 在 pgAdmin 容器內部連線時使用容器名稱作為 Host（如 `postgres-data`），不要用 `localhost`。

---

## Port 衝突排除

如果你本機已有其他服務佔用了預設 port，可以用以下方式排查和解決。

### 查看 port 是否被佔用

```bash
# macOS / Linux
lsof -i :5432   # PostgreSQL
lsof -i :8080   # Frontend
lsof -i :8088   # Backend
lsof -i :8889   # pgAdmin
lsof -i :6333   # Qdrant
```

### 解決方式：手動啟動容器並換 port

如果 `docker compose up` 因 port 衝突失敗，可以只啟動不衝突的服務，然後手動啟動衝突的容器。

**範例：Port 5432 被佔用**

```bash
# 只啟動不衝突的服務
docker compose -f docker-compose-db.yaml up -d redis postgres-data pgadmin qdrant

# 手動啟動 postgres-manager，將 host port 改為 5433
docker run -d --name postgres-manager --network br_dashboard --restart always \
  -e POSTGRES_DB=dashboardmanager \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=你的密碼 \
  -v postgres_manager_data:/var/lib/postgresql/data \
  -p 5433:5432 \
  postgis/postgis:16-3.4-alpine
```

**範例：Port 8080 被佔用（前端）**

```bash
# 手動啟動前端，將 host port 改為 3000
docker rm -f dashboard-fe 2>/dev/null
docker run -d --name dashboard-fe --network br_dashboard --restart always \
  -e DOCKER_COMPOSE=true \
  -e NODE_ENV=development \
  -e VITE_API_URL=/api/dev \
  -e VITE_APP_TITLE="臺北城市儀表板" \
  -e VITE_APP_VERSION=2.0.0 \
  -v "$(pwd)/../Taipei-City-Dashboard-FE:/opt/Taipei-City-Dashboard-FE" \
  -w /opt/Taipei-City-Dashboard-FE \
  -p 3000:80 \
  node:21.6.0-alpine3.18 \
  npm run dev
```

> 此時前端改為 http://localhost:3000 存取。

---

## 常用維運指令

### 查看服務狀態

```bash
# 查看所有相關容器
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "dashboard|postgres|redis|qdrant|pgadmin|nginx"
```

### 查看 Log

```bash
# 即時查看前端 log
docker logs -f dashboard-fe

# 即時查看後端 log
docker logs -f dashboard-be

# 查看最近 50 行
docker logs --tail 50 dashboard-be
```

### 重啟服務

```bash
# 重啟單一服務
docker restart dashboard-fe
docker restart dashboard-be

# 重啟所有應用服務
docker compose -f docker-compose.yaml restart dashboard-fe dashboard-be

# 重啟所有 DB 服務
docker compose -f docker-compose-db.yaml restart
```

### 停止服務

```bash
# 停止應用服務（保留 DB）
docker compose -f docker-compose.yaml stop

# 停止 DB 服務
docker compose -f docker-compose-db.yaml stop

# 停止所有相關容器
docker stop dashboard-fe dashboard-be postgres-data postgres-manager redis qdrant pgadmin
```

---

## 完整清除（重新來過）

如果你想完全清除所有容器和資料，重新開始：

```bash
cd docker

# 1. 停止並移除所有容器
docker compose -f docker-compose.yaml down
docker compose -f docker-compose-db.yaml down

# 若有手動啟動的容器也要清除
docker rm -f dashboard-fe dashboard-be postgres-manager 2>/dev/null

# 2. 移除 Docker Volumes（會刪除所有資料庫資料！）
docker volume rm redis_data postgres_data postgres_manager_data pgadmin_data qdrant_data 2>/dev/null

# 3. 移除 Docker 網路
docker network rm br_dashboard

# 4. （可選）移除後端 Image
docker rmi dashboard-be-dev:latest

# 5. 完成，可以從 Step 2 重新開始部署
```

> **⚠️ 警告：** 執行以上指令會**刪除所有資料庫資料**，請確認你不需要保留這些資料。

---

## 常見問題 FAQ

### Q: `Cannot connect to the Docker daemon` 是什麼意思？

**A:** Docker Desktop 沒有啟動。請開啟 Docker Desktop 並等待它完全就緒：
```bash
open -a Docker  # macOS
# 等待約 10-30 秒
docker info > /dev/null 2>&1 && echo "Ready!"
```

### Q: 前端可以打開但看不到資料/圖表？

**A:** 確認後端 (`dashboard-be`) 是否正常運行：
```bash
docker logs dashboard-be 2>&1 | tail -5
# 應看到 [info] 0.0.0.0:8080
```
如果後端有錯誤，檢查資料庫是否已正確初始化（Step 4）。

### Q: `image platform does not match` 警告？

**A:** 如果你使用 Apple Silicon (M1/M2/M3/M4) Mac，某些映像可能顯示此警告。這通常不影響功能，Docker 會自動以模擬方式運行 x86 映像。

### Q: 初始化時 `go: downloading ...` 很慢？

**A:** Go module 下載速度取決於網路。首次下載可能需要 1-3 分鐘，後續執行會使用快取。如果網路問題嚴重，可考慮設定 Go proxy：
```bash
# 在 .env 中加入（選用）
GOPROXY=https://goproxy.io,direct
```

### Q: 地圖不顯示？

**A:** 地圖功能需要 Mapbox Token。在 `.env` 中填入你的 Mapbox Token：
```dotenv
VITE_MAPBOXTOKEN=pk.your_mapbox_token_here
VITE_MAPBOXTILE=mapbox://styles/your_style
```
到 [Mapbox](https://www.mapbox.com/) 免費註冊即可取得 Token。

### Q: AI Chat 功能無法使用？

**A:** AI Chat 需要 TWCC AI Foundry 的 API Key。在 `.env` 中填入：
```dotenv
TWCC_API_KEY=你的_TWCC_API_Key
```

### Q: 如何只重新 Build 後端（程式碼改動後）？

**A:** 由於開發模式使用 volume mount + `go run`，**後端程式碼改動會自動生效**，只需要重啟容器：
```bash
docker restart dashboard-be
```

如果改動了 Dockerfile 或需要更新 ONNX 模型，才需要重新 build image：
```bash
docker build --target dev -t dashboard-be-dev:latest ../Taipei-City-Dashboard-BE/
docker restart dashboard-be
```

### Q: 如何只重建前端（不影響其他服務）？

**A:** 前端也是 volume mount + Vite dev server，程式碼改動會自動 **Hot Reload**，不需要任何操作。

---

## 附錄：Compose 檔案結構

```
docker/
├── .env.template              # 環境變數模板（複製為 .env 使用）
├── .env                       # 你的環境變數（不會進 git）
├── docker-compose-db.yaml     # 資料庫 & 基礎設施服務
├── docker-compose-init.yaml   # 一次性初始化任務
├── docker-compose.yaml        # 主要應用服務（FE + BE + Nginx）
├── nginx/
│   └── conf.d/
│       └── default.conf       # Nginx 反向代理設定
└── qdrant-upgrade/            # Qdrant 向量資料庫升級腳本
```

| 檔案 | 用途 | 何時執行 |
|------|------|----------|
| `docker-compose-db.yaml` | 啟動 PostgreSQL、Redis、Qdrant、pgAdmin | 最先執行，常駐運行 |
| `docker-compose-init.yaml` | npm ci、DB migration、匯入範例資料 | 首次部署或需要重建 DB 時 |
| `docker-compose.yaml` | 啟動 Frontend、Backend、Nginx | DB 就緒後執行，常駐運行 |
