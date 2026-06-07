LINE OA 好友數監控
每日自動抓取台灣房地產競品 LINE Official Account 公開好友數，並存入 CSV。
監控帳號
名稱	LINE OA
5168實登	https://page.line.me/399tasev
5168買屋	https://page.line.me/119qavtz
591房屋	https://page.line.me/qxx7167w
樂居	https://page.line.me/prm0754f
樂屋	https://page.line.me/506lijcv
專案結構
```
line-monitor/
├── .github/
│   └── workflows/
│       └── scrape.yml      # GitHub Actions 排程設定
├── data/
│   └── history.csv         # 歷史好友數資料（自動累積）
├── scripts/
│   └── scraper.py          # 主爬蟲程式
├── requirements.txt
└── README.md
```
快速開始（GitHub Actions 自動排程）
步驟 1：建立 GitHub Repository
前往 github.com 建立新的 private repository
名稱建議：`line-oa-monitor`
步驟 2：上傳專案
```bash
git init
git add .
git commit -m "init: LINE OA 好友數監控"
git branch -M main
git remote add origin https://github.com/你的帳號/line-oa-monitor.git
git push -u origin main
```
步驟 3：確認 Actions 權限
進入 GitHub repo → Settings → Actions → General
在 Workflow permissions 選 Read and write permissions
勾選 Allow GitHub Actions to create and approve pull requests
點 Save
步驟 4：等待或手動觸發
自動執行：每天台灣時間 10:00（UTC 02:00）自動執行
手動執行：
進入 repo → Actions → 每日抓取 LINE OA 好友數
點 Run workflow → Run workflow
執行後，`data/history.csv` 會自動被 bot commit 回 repo。
---
本機執行（測試用）
```bash
# 安裝套件
pip install -r requirements.txt

# 執行一次
python scripts/scraper.py

# 強制覆蓋今日資料
FORCE=1 python scripts/scraper.py
```
---
CSV 格式
```
date,reg5168,buy5168,f591,leju,lehu
2026-06-07,12345,23456,1745028,71110,89000
2026-06-08,12400,23500,1746000,71300,89200
```
欄位說明：
`date`：台灣日期（YYYY-MM-DD）
`reg5168`：5168實登好友數
`buy5168`：5168買屋好友數
`f591`：591房屋好友數
`leju`：樂居好友數
`lehu`：樂屋好友數
---
將 CSV 接上儀表板
儀表板讀取 CSV 的方式（以 GitHub raw URL 為例）：
```javascript
const CSV_URL =
  "https://raw.githubusercontent.com/你的帳號/line-oa-monitor/main/data/history.csv";

const resp = await fetch(CSV_URL);
const text = await resp.text();
// 用 PapaParse 解析
const { data } = Papa.parse(text, { header: true, dynamicTyping: true });
```
---
常見問題
Q：爬蟲抓到空值怎麼辦？
A：CSV 該欄留空，不影響其他帳號。GitHub Actions 會以 warning（exit 1）標記，你可到 Actions 頁面查看詳情。
Q：LINE 改版導致格式變更？
A：`page.line.me` 頁面的好友數以 `Friends 1,234,567` 格式呈現於靜態 HTML，LINE 鮮少更動此格式。若失效，只需調整 `scraper.py` 中的正則表達式。
Q：可以加通知嗎？
A：可在 `scrape.yml` 結尾加入 Slack / LINE Notify / Email 步驟。
