# 捷運最後一哩服務健康度 Ubuntu 部署說明

這包是靜態前端 + Python 資料更新器。Python 腳本會抓取 TDX 捷運站、YouBike 與公車 ETA 真實資料，輸出 `current_data.json`，並把每次站點服務健康度快照追加到 `last_mile_service_history.jsonl`。

## 內容

- `index.html`、`styles.css`、`script.js`：前端儀表板
- `metro_routes/*.geojson`：捷運路線實際 geometry
- `update_data.py`：資料抓取與歷史快照累積
- `current_data.json`：目前前端讀取的最新資料
- `last_mile_service_history.jsonl`：歷史快照檔，第一次執行後會開始累積

## Ubuntu 原地部署指令

假設 zip 檔名是 `rain-commute-cbmf-service.zip`，會部署到 `/opt/rain-commute-cbmf-service`。

```bash
sudo apt update
sudo apt install -y python3 nginx unzip

cd /tmp
sudo unzip -o rain-commute-cbmf-service.zip -d /opt

sudo chown -R www-data:www-data /opt/rain-commute-cbmf-service
sudo find /opt/rain-commute-cbmf-service -type d -exec chmod 755 {} \;
sudo find /opt/rain-commute-cbmf-service -type f -exec chmod 644 {} \;

sudo -u www-data python3 /opt/rain-commute-cbmf-service/update_data.py
```

## 設定每 5 分鐘自動抓資料

```bash
sudo tee /etc/systemd/system/rain-cbmf-update.service >/dev/null <<'EOF'
[Unit]
Description=Metro last-mile service health data updater
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/opt/rain-commute-cbmf-service
ExecStart=/usr/bin/python3 /opt/rain-commute-cbmf-service/update_data.py
EOF

sudo tee /etc/systemd/system/rain-cbmf-update.timer >/dev/null <<'EOF'
[Unit]
Description=Run metro last-mile service updater every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now rain-cbmf-update.timer
sudo systemctl start rain-cbmf-update.service
sudo systemctl status rain-cbmf-update.timer
```

查看更新紀錄：

```bash
sudo journalctl -u rain-cbmf-update.service -n 50 --no-pager
sudo tail -n 5 /opt/rain-commute-cbmf-service/last_mile_service_history.jsonl
```

## 用 Nginx 對外提供前端

如果這台伺服器只跑這個服務，可以直接用預設站台：

```bash
sudo tee /etc/nginx/sites-available/rain-cbmf >/dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    root /opt/rain-commute-cbmf-service;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~* \.(json|geojson)$ {
        add_header Cache-Control "no-store";
        try_files $uri =404;
    }
}
EOF

sudo ln -sfn /etc/nginx/sites-available/rain-cbmf /etc/nginx/sites-enabled/rain-cbmf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

然後打開：

```text
http://你的伺服器IP/
```

## 更新部署包

之後如果拿到新版 zip：

```bash
cd /tmp
sudo unzip -o rain-commute-cbmf-service.zip -d /opt
sudo chown -R www-data:www-data /opt/rain-commute-cbmf-service
sudo systemctl start rain-cbmf-update.service
sudo systemctl reload nginx
```

如果你想保留伺服器上的歷史資料，更新前先備份：

```bash
sudo cp /opt/rain-commute-cbmf-service/last_mile_service_history.jsonl /tmp/last_mile_service_history.backup.jsonl
sudo unzip -o rain-commute-cbmf-service.zip -d /opt
sudo cp /tmp/last_mile_service_history.backup.jsonl /opt/rain-commute-cbmf-service/last_mile_service_history.jsonl
sudo chown www-data:www-data /opt/rain-commute-cbmf-service/last_mile_service_history.jsonl
```
