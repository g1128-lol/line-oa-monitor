"""
LINE OA 好友數爬蟲
抓取房地產競品 LINE Official Account 的公開好友數
並將結果追加到 data/history.csv

用法：
    python scripts/scraper.py
    FORCE=1 python scripts/scraper.py   # 強制覆蓋今日
"""

import csv
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── 設定區 ──────────────────────────────────────────────────────────────────

ACCOUNTS = [
    {"name": "5168實登",  "url": "https://page.line.me/399tasev", "key": "reg5168"},
    {"name": "5168買屋",  "url": "https://page.line.me/119qavtz", "key": "buy5168"},
    {"name": "591房屋",   "url": "https://page.line.me/qxx7167w", "key": "f591"},
    {"name": "樂居",      "url": "https://page.line.me/prm0754f", "key": "leju"},
    {"name": "樂屋",      "url": "https://page.line.me/506lijcv", "key": "lehu"},
]

DATA_DIR  = Path(__file__).parent.parent / "data"
CSV_PATH  = DATA_DIR / "history.csv"
CSV_COLS  = ["date"] + [a["key"] for a in ACCOUNTS]

# 台灣時間 UTC+8
TW_TZ = timezone(timedelta(hours=8))

# 模擬真實 Chrome 瀏覽器，通過 LINE 的 bot 過濾
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

REQUEST_TIMEOUT = 25   # 秒
RETRY_TIMES     = 3    # 每個帳號最多重試次數
RETRY_DELAY     = 8    # 重試間隔（秒）
BETWEEN_DELAY   = 3    # 每次請求之間的等待（秒，避免觸發速率限制）

# ── 核心函式 ─────────────────────────────────────────────────────────────────

def fetch_friends(url: str, retries: int = RETRY_TIMES) -> int | None:
    """
    抓取指定 LINE OA 頁面的好友數。

    page.line.me 靜態 HTML 結構範例：
        <span ...>Friends 1,745,028</span>

    此格式為 LINE 官方頁面固定格式，不依賴 JS 渲染，
    requests + BeautifulSoup 可直接解析。
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()

            # 策略1：BeautifulSoup 搜尋含 "Friends" 的文字節點
            soup = BeautifulSoup(resp.text, "lxml")
            for text_node in soup.find_all(string=re.compile(r"Friends\s+[\d,]+", re.I)):
                m = re.search(r"Friends\s+([\d,]+)", str(text_node), re.I)
                if m:
                    return int(m.group(1).replace(",", ""))

            # 策略2：全文 regex（備用，處理 HTML 實體等狀況）
            m = re.search(r"Friends\s+([\d,]+)", resp.text, re.I)
            if m:
                return int(m.group(1).replace(",", ""))

            # 策略3：搜尋 JSON-LD 或 meta 標籤（未來可能的格式）
            for tag in soup.find_all("meta"):
                content = tag.get("content", "")
                m = re.search(r"Friends\s+([\d,]+)", content, re.I)
                if m:
                    return int(m.group(1).replace(",", ""))

            print(f"  [WARN] 找不到好友數（HTTP {resp.status_code}）：{url}")
            print(f"  [DEBUG] 回應前 500 字：{resp.text[:500]!r}")
            return None

        except requests.HTTPError as e:
            print(f"  [ERR] HTTP 錯誤 第 {attempt} 次 ({url}): {e}")
        except requests.Timeout:
            print(f"  [ERR] 請求逾時 第 {attempt} 次 ({url})")
        except requests.RequestException as e:
            print(f"  [ERR] 請求失敗 第 {attempt} 次 ({url}): {e}")

        if attempt < retries:
            print(f"  ↩  {RETRY_DELAY} 秒後重試...")
            time.sleep(RETRY_DELAY)

    return None


def load_existing_dates() -> set:
    """讀取 CSV 中已有的日期，避免重複寫入同一天。"""
    if not CSV_PATH.exists():
        return set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["date"] for row in reader}


def append_row(row: dict) -> None:
    """將一筆資料追加到 CSV；若檔案不存在則建立並寫入標頭。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ── 主程式 ───────────────────────────────────────────────────────────────────

def main():
    today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    print(f"=== LINE OA 好友數爬蟲 | {today} ===\n")

    # 已有今天資料則跳過（允許強制覆蓋）
    if today in load_existing_dates() and not os.getenv("FORCE"):
        print(f"今日 ({today}) 資料已存在，略過。")
        print("若要強制重跑請設環境變數 FORCE=1")
        sys.exit(0)

    row = {"date": today}
    failed = []

    for account in ACCOUNTS:
        print(f"抓取：{account['name']}")
        print(f"  URL：{account['url']}")
        count = fetch_friends(account["url"])

        if count is not None:
            row[account["key"]] = count
            print(f"  ✓ 好友數：{count:,}\n")
        else:
            row[account["key"]] = ""
            failed.append(account["name"])
            print(f"  ✗ 取得失敗，本日記錄留空\n")

        time.sleep(BETWEEN_DELAY)

    append_row(row)

    print("─" * 50)
    print(f"✅ 已寫入 {CSV_PATH}")
    print(f"   日期：{today}")
    for acc in ACCOUNTS:
        val = row[acc["key"]]
        display = f"{val:,}" if isinstance(val, int) else "（失敗）"
        print(f"   {acc['name']:<10} {display}")

    if failed:
        print(f"\n⚠️  失敗帳號：{', '.join(failed)}")
        print("請至 GitHub Actions 查看詳細錯誤，或手動確認該 OA 頁面。")
        sys.exit(1)
    else:
        print("\n✨ 全部抓取成功！")


if __name__ == "__main__":
    main()
