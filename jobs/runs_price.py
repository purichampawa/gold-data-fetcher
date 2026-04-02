import sys
import os
import json
import threading
from flask import Flask # ต้อง pip install flask
from datetime import datetime, timedelta
import pytz 
from playwright.sync_api import sync_playwright
from supabase import create_client, Client
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.gold_interceptor import run

# 1. ตั้งค่า Flask เพื่อใช้เป็น Health Check สำหรับ Render แผน Free
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Gold Fetcher Status: ONLINE", 200

parser = argparse.ArgumentParser()
parser.add_argument("--once", action="store_true")
args = parser.parse_args()


# 2. ตั้งค่า Supabase และเวลา
from dotenv import load_dotenv
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

last_saved_time = None
BKK_TZ = pytz.timezone('Asia/Bangkok')

def is_market_open(now_time):
    weekday = now_time.weekday() # 0=Mon, 6=Sun
    hour_float = now_time.hour + (now_time.minute / 60.0)
    if weekday < 5: # จันทร์-ศุกร์
        return not (2.0 <= hour_float < 6.0)
    else: # เสาร์-อาทิตย์
        return 9.5 <= hour_float < 17.5

def handle_new_price(price_data: dict):
    global last_saved_time
    now = datetime.now(BKK_TZ)
    if not is_market_open(now):
        return 
    if last_saved_time is None or (now - last_saved_time) >= timedelta(minutes=5):
        try:
            supabase.table("gold_prices").insert(price_data).execute()
            print(f"🔔 [DB SAVED] {price_data['timestamp']} | Spot: {price_data['spot_price']}")
            last_saved_time = now 
        except Exception as e:
            print(f"❌ Error: {e}")

def start_price_interceptor(once_mode=False):
    print(f"🚀 [JOB: PRICE] เริ่มต้นการดักจับราคาทองคำ... (Once Mode: {once_mode})")
    with sync_playwright() as playwright:
        # ส่งค่า once_mode เข้าไปใน modules.gold_interceptor
        run(playwright, callback=handle_new_price, once=once_mode)

if __name__ == "__main__":
    # เช็ค Arguments ว่าสั่งรันแบบรอบเดียวหรือไม่
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        # ถ้าสั่ง --once (สำหรับ GitHub Actions) ให้รันฟังก์ชันโดยตรงแล้วจบงาน
        start_price_interceptor(once_mode=True)
    else:
        # ถ้าไม่ใส่ --once (สำหรับรัน Local ใน MacBook) ให้รัน Flask และ Thread ปกติ
        price_thread = threading.Thread(target=lambda: start_price_interceptor(once_mode=False), daemon=True)
        price_thread.start()
        
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port)