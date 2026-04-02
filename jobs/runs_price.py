import sys
import os
import argparse
import threading
from flask import Flask
from datetime import datetime, timedelta
import pytz 
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
from dotenv import load_dotenv

# นำเข้าโมดูลดักราคา
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.gold_interceptor import run

load_dotenv()
app = Flask(__name__)

# ตั้งค่า Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

BKK_TZ = pytz.timezone('Asia/Bangkok')
last_saved_time = None

def is_market_open(now_time):
    weekday = now_time.weekday()
    hour_float = now_time.hour + (now_time.minute / 60.0)
    if weekday < 5: # จันทร์-ศุกร์
        return not (2.0 <= hour_float < 6.0)
    else: # เสาร์-อาทิตย์
        return 9.5 <= hour_float < 17.5

def handle_new_price(price_data: dict):
    global last_saved_time
    now = datetime.now(BKK_TZ)
    if not is_market_open(now): return 

    # บันทึกทุก 5 นาที
    if last_saved_time is None or (now - last_saved_time) >= timedelta(minutes=5):
        try:
            supabase.table("gold_prices").insert(price_data).execute()
            print(f"🔔 [DB SAVED] {price_data['timestamp']} | Spot: {price_data['spot_price']}")
            last_saved_time = now 
        except Exception as e:
            print(f"❌ DB Error: {e}")

def start_price_interceptor(once_mode=False):
    print(f"🚀 [JOB: PRICE] เริ่มต้นงานดักราคา... (Once Mode: {once_mode})")
    with sync_playwright() as playwright:
        run(playwright, callback=handle_new_price, once=once_mode)

@app.route('/')
def health_check():
    return "Gold Fetcher Status: ONLINE", 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        # สำหรับรันบน GitHub Actions
        start_price_interceptor(once_mode=True)
    else:
        # สำหรับรันบน MacBook
        threading.Thread(target=lambda: start_price_interceptor(once_mode=False), daemon=True).start()
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port)