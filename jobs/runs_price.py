import sys
import os
import json
from datetime import datetime, timedelta
import pytz # 👈 ไลบรารีสำหรับจัดการเวลาไทย
from playwright.sync_api import sync_playwright
from supabase import create_client, Client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.gold_interceptor import run

# ดึง Config จาก .env
from dotenv import load_dotenv
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ตัวแปรจำเวลาล่าสุดที่เซฟข้อมูลลง DB
last_saved_time = None
BKK_TZ = pytz.timezone('Asia/Bangkok')

def is_market_open(now_time):
    """ฟังก์ชันเช็คเวลาเปิด-ปิดตลาดทองตามที่กำหนด"""
    weekday = now_time.weekday() # 0=จันทร์, 1=อังคาร, ..., 4=ศุกร์, 5=เสาร์, 6=อาทิตย์
    # แปลงเวลาเป็นทศนิยมเพื่อง่ายต่อการเปรียบเทียบ (เช่น 9:30 = 9.5)
    hour_float = now_time.hour + (now_time.minute / 60.0)

    if weekday < 5: # วันจันทร์ - ศุกร์
        # ให้หยุดรันช่วง 02:00 - 06:00
        if 2.0 <= hour_float < 6.0: 
            return False
        return True # เวลาอื่นของวันธรรมดา ให้รันปกติ
    else: # วันเสาร์ - อาทิตย์
        # ให้รันแค่ช่วง 09:30 - 17:30
        if 9.5 <= hour_float < 17.5:
            return True
        return False # เวลาอื่นของเสาร์อาทิตย์ ให้ปิด

def handle_new_price(price_data: dict):
    global last_saved_time
    now = datetime.now(BKK_TZ)

    # 1. เช็คก่อนว่าอยู่ในช่วงเวลาที่ตลาดเปิดไหม?
    if not is_market_open(now):
        # ถ้านอกเวลา ไม่ต้องทำอะไร ปล่อยผ่านไปเลย
        return 

    # 2. เช็คว่าเวลาปัจจุบัน ห่างจากครั้งล่าสุดที่เซฟ ครบ 5 นาทีหรือยัง?
    if last_saved_time is None or (now - last_saved_time) >= timedelta(minutes=5):
        try:
            # 🌟 ยิงข้อมูลแถวเดียวเข้าตาราง gold_prices
            response = supabase.table("gold_prices").insert(price_data).execute()
            print(f"🔔 [DB SAVED] {price_data['timestamp']} | Spot: {price_data['spot_price']}")
            
            # อัปเดตเวลาที่เซฟครั้งล่าสุด
            last_saved_time = now 
        except Exception as e:
            print(f"❌ Error บันทึกราคา: {e}")

def main():
    print("🚀 [JOB: PRICE] เริ่มต้นการดักจับราคาทองคำ Real-time...")
    with sync_playwright() as playwright:
        run(playwright, callback=handle_new_price)

if __name__ == "__main__":
    main()