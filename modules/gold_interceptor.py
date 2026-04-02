from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import os  # เพิ่ม import os เพื่อความชัวร์


def run(playwright, callback, once=False):
    # 1. เพิ่ม args เพื่อประหยัดทรัพยากรบน GitHub
    browser = playwright.chromium.launch(
        headless=True, args=["--disable-dev-shm-usage"]
    )
    context = browser.new_context(user_agent="Mozilla/5.0...")

    # 2. ตั้งค่า Timeout พื้นฐานให้ยาวขึ้นเป็น 60 วินาที
    context.set_default_timeout(60000)
    page = context.new_page()

    state = {"is_finished": False}

    def process_message(payload, callback):
        if state["is_finished"]:
            return
        if payload.startswith("42"):
            try:
                data_list = json.loads(payload[2:])
                if data_list[0] == "updateGoldRateData":
                    gold = data_list[1]
                    t_stamp = gold.get("createDate", "Unknown")
                    bid_99 = gold.get("bidPrice99")
                    ask_99 = gold.get("offerPrice99")
                    bid_96 = gold.get("bidPrice96")
                    ask_96 = gold.get("offerPrice96")
                    spot = gold.get("AUXBuy")
                    fx = gold.get("usdBuy")
                    a_bid = gold.get("bidCentralPrice96")
                    a_ask = gold.get("offerCentralPrice96")

                    data_row = {
                        "timestamp": t_stamp,
                        "bid_99": bid_99,
                        "ask_99": ask_99,
                        "bid_96": bid_96,
                        "ask_96": ask_96,
                        "spot_price": spot,
                        "usd_thb": fx,
                        "assoc_bid": a_bid,
                        "assoc_ask": a_ask,
                    }

                    def fmt(val):
                        if val is None:
                            return "N/A"
                        try:
                            return (
                                f"{float(val):,.0f}"
                                if float(val) >= 1000
                                else f"{float(val):,.2f}"
                            )
                        except ValueError:
                            return "N/A"

                    print(
                        f"🌟 [99.99%] {t_stamp} | Buy: {fmt(bid_99)} | Sell: {fmt(ask_99)}"
                    )
                    print(
                        f"✅ [96.5%]  {t_stamp} | Buy: {fmt(bid_96)} | Sell: {fmt(ask_96)}"
                    )
                    print(f"🌐 [GLOBAL] Spot: {fmt(spot)} | USD/THB: {fmt(fx)}")
                    print("-" * 75)

                    if callback:
                        callback(data_row)

                    if once:
                        print("🛑 [ONCE MODE] บันทึกสำเร็จ! กำลังเตรียมปิดระบบ...")
                        state["is_finished"] = True
            except Exception:
                pass

    page.on(
        "websocket",
        lambda ws: ws.on("framereceived", lambda p: process_message(p, callback)),
    )

    # 3. เปลี่ยน wait_until เป็น 'commit' หรือ 'domcontentloaded' เพื่อให้มันเริ่มดัก WebSocket เร็วขึ้น
    try:
        page.goto(
            "https://www.intergold.co.th/curr-price/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
    except Exception as e:
        print(f"⚠️ Page Load Warning: {e} (แต่อาจจะดัก WebSocket ได้แล้ว)")

    try:
        if once:
            start_time = datetime.now()
            while not state["is_finished"]:
                page.wait_for_timeout(1000)
                if (datetime.now() - start_time).seconds > 120:
                    break
        else:
            while True:
                page.wait_for_timeout(60000)
    finally:
        print("🛑 Closing browser...")
        browser.close()
