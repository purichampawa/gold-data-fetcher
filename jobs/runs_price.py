import sys
import os
import json
import threading
from flask import Flask # ต้อง pip install flask
from datetime import datetime, timedelta
import pytz 
from playwright.sync_api import sync_playwright
from supabase import create_client, Client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.gold_interceptor import run

# 1. ตั้งค่า Flask เพื่อใช้เป็น Health Check สำหรับ Render แผน Free
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Gold Fetcher Status: ONLINE", 200

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

# 3. ฟังก์ชันหลักสำหรับรันงานดักราคา
def start_price_interceptor():
    print("🚀 [JOB: PRICE] เริ่มต้นการดักจับราคาทองคำ...")
    with sync_playwright() as playwright:
        run(playwright, callback=handle_new_price)

if __name__ == "__main__":
    # รันงานดักราคาไว้ที่พื้นหลัง (Background Thread)
    price_thread = threading.Thread(target=start_price_interceptor, daemon=True)
    price_thread.start()
    
    # รัน Flask บน Port ที่ Render กำหนด (Default คือ 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)