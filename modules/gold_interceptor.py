from playwright.sync_api import sync_playwright
import json
import os

def run(playwright, callback, once=False):
    # รัน chromium แบบ headless (ไม่เปิดหน้าต่าง) เพื่อใช้บน Server
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    page = context.new_page()

    print("🚀 Opening browser to intercept WebSocket stream...")

    def process_message(payload, callback):
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

                    # แสดงผลบน Log
                    print(f"🌟 [99.99%] {t_stamp} | Spot: {gold.get('AUXBuy')} | USD/THB: {gold.get('usdBuy')}")
                    
                    if callback:
                        callback(data_row)

                    # ถ้าเป็นโหมด Once ให้สะกิดให้ระบบหยุดทำงานอย่างนุ่มนวล
                    if once:
                        print("🛑 [ONCE MODE] บันทึกข้อมูลสำเร็จ กำลังเตรียมปิดระบบ...")
                        raise StopIteration

            except StopIteration:
                raise StopIteration # ส่งต่อเพื่อให้ Loop ด้านล่างจับได้
            except Exception:
                pass

    def on_websocket(ws):
        ws.on("framereceived", lambda payload: process_message(payload, callback))

    page.on("websocket", on_websocket)
    page.goto("https://www.intergold.co.th/curr-price/", wait_until="networkidle")

    try:
        if once:
            # รอสูงสุด 2 นาที เผื่อเน็ตช้า
            page.wait_for_timeout(120000) 
        else:
            while True:
                page.wait_for_timeout(60000) 
    except (StopIteration, KeyboardInterrupt):
        print("\n🛑 Closing browser gracefully...")
        browser.close()
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        browser.close()