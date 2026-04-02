from playwright.sync_api import sync_playwright
import json
from datetime import datetime

def run(playwright, callback, once=False):
    # เปิด Browser แบบ Headless สำหรับ GitHub Actions
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    page = context.new_page()
    
    # ใช้ dictionary เก็บสถานะเพื่อให้เรียกใช้ข้ามฟังก์ชันได้
    state = {"is_finished": False}

    print("🚀 Opening browser to intercept WebSocket stream...")

    def process_message(payload, callback):
        # ถ้าได้ข้อมูลไปแล้ว (ในโหมด once) ให้ข้ามเฟรมถัดๆ ไปเลย
        if state["is_finished"]:
            return

        if payload.startswith("42"):
            try:
                data_list = json.loads(payload[2:])
                if data_list[0] == "updateGoldRateData":
                    gold = data_list[1]
                    t_stamp = gold.get("createDate", "Unknown")

                    data_row = {
                        "timestamp": t_stamp,
                        "bid_99": gold.get("bidPrice99"),
                        "ask_99": gold.get("offerPrice99"),
                        "bid_96": gold.get("bidPrice96"),
                        "ask_96": gold.get("offerPrice96"),
                        "spot_price": gold.get("AUXBuy"),
                        "usd_thb": gold.get("usdBuy"),
                        "assoc_bid": gold.get("bidCentralPrice96"),
                        "assoc_ask": gold.get("offerCentralPrice96")
                    }

                    print(f"🌟 [99.99%] {t_stamp} | Spot: {gold.get('AUXBuy')} | USD/THB: {gold.get('usdBuy')}")
                    
                    if callback:
                        callback(data_row)

                    # ถ้าเป็นโหมด Once ให้เปลี่ยนสถานะเพื่อให้ Loop หลักหยุดทำงาน
                    if once:
                        print("🛑 [ONCE MODE] บันทึกข้อมูลสำเร็จ กำลังเตรียมปิดระบบ...")
                        state["is_finished"] = True

            except Exception:
                pass

    def on_websocket(ws):
        ws.on("framereceived", lambda payload: process_message(payload, callback))

    page.on("websocket", on_websocket)
    page.goto("https://www.intergold.co.th/curr-price/", wait_until="networkidle")

    try:
        if once:
            # วนลูปเช็คสถานะทุก 1 วินาที (สูงสุด 2 นาทีป้องกันค้าง)
            start_time = datetime.now()
            while not state["is_finished"]:
                page.wait_for_timeout(1000) 
                if (datetime.now() - start_time).seconds > 120:
                    print("⚠️ Timeout: ไม่ได้รับข้อมูลภายใน 2 นาที")
                    break
        else:
            # โหมดปกติ (MacBook) ให้รันค้างไว้
            while True:
                page.wait_for_timeout(60000) 
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Closing browser...")
        browser.close()