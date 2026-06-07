import csv, os, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

ACCOUNTS = [
    {"name": "5168實登", "url": "https://page.line.me/399tasev", "key": "reg5168"},
    {"name": "5168買屋", "url": "https://page.line.me/119qavtz", "key": "buy5168"},
    {"name": "591房屋",  "url": "https://page.line.me/qxx7167w", "key": "f591"},
    {"name": "樂居",     "url": "https://page.line.me/prm0754f", "key": "leju"},
    {"name": "樂屋",     "url": "https://page.line.me/506lijcv", "key": "lehu"},
]

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "history.csv"
CSV_COLS = ["date"] + [a["key"] for a in ACCOUNTS]
TW_TZ = timezone(timedelta(hours=8))

def fetch_friends(page, url):
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        text = page.inner_text("body")
        # 中文版：好友人數 71,110
        m = re.search(r"好友人數\s*([\d,]+)", text)
        if m:
            return int(m.group(1).replace(",", ""))
        # 英文版：Friends 1,745,028
        m = re.search(r"Friends\s+([\d,]+)", text)
        if m:
            return int(m.group(1).replace(",", ""))
        # 網頁原始碼
        content = page.content()
        m = re.search(r"好友人數\s*([\d,]+)", content)
        if m:
            return int(m.group(1).replace(",", ""))
        m = re.search(r"Friends\s+([\d,]+)", content)
        if m:
            return int(m.group(1).replace(",", ""))
        print(f"  [WARN] 找不到好友數，頁面文字前300字：{text[:300]!r}")
        return None
    except Exception as e:
        print(f"  [ERR] {e}")
        return None

def load_existing_dates():
    if not CSV_PATH.exists():
        return set()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {row["date"] for row in csv.DictReader(f)}

def append_row(row):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def main():
    today = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    print(f"=== LINE OA 好友數爬蟲 | {today} ===\n")
    if today in load_existing_dates() and not os.getenv("FORCE"):
        print("今日資料已存在，略過。")
        sys.exit(0)
    row = {"date": today}
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="zh-TW",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        for account in ACCOUNTS:
            print(f"抓取：{account['name']} ({account['url']})")
            count = fetch_friends(page, account["url"])
            if count is not None:
                row[account["key"]] = count
                print(f"  ✓ {count:,}\n")
            else:
                row[account["key"]] = ""
                failed.append(account["name"])
                print(f"  ✗ 失敗\n")
            time.sleep(3)
        browser.close()
    append_row(row)
    print(f"✅ 已寫入 {CSV_PATH}")
    if failed:
        print(f"⚠️ 失敗：{', '.join(failed)}")
        sys.exit(1)
    else:
        print("✨ 全部成功！")

if __name__ == "__main__":
    main()
