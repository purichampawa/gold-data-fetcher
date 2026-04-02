from playwright.sync_api import sync_playwright
import json

def run(playwright, callback=None):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    print("🚀 Opening browser to intercept WebSocket stream...")

    def on_websocket(ws):
        ws.on("framereceived", lambda payload: process_message(payload, callback))

    def process_message(payload, callback):
        if payload.startswith("42"):
            try:
                data_list = json.loads(payload[2:])
                event_name = data_list[0]

                if event_name == "updateGoldRateData":
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
                        "assoc_ask": a_ask
                    }

                    def fmt(val):
                        if val is None: return "N/A"
                        try:
                            return f"{float(val):,.0f}" if float(val) >= 1000 else f"{float(val):,.2f}"
                        except ValueError:
                            return "N/A"

                    print(f"🌟 [99.99%] {t_stamp} | Buy: {fmt(bid_99)} | Sell: {fmt(ask_99)}")
                    print(f"✅ [96.5%]  {t_stamp} | Buy: {fmt(bid_96)} | Sell: {fmt(ask_96)}")
                    print(f"🌐 [GLOBAL] Spot: {fmt(spot)} | USD/THB: {fmt(fx)}")
                    print("-" * 75)

                    if callback:
                        callback(data_row)

            except Exception as e:
                pass

    page.on("websocket", on_websocket)
    # รอจนกว่า network จะนิ่ง แปลว่าโหลดหน้าเว็บเสร็จสมบูรณ์
    page.goto("https://www.intergold.co.th/curr-price/", wait_until="networkidle")

    print(f"📡 Intercepting live prices... (Press Ctrl+C to stop)")

    try:
        while True:
            # ให้มันรอทีละ 1 นาทีวนไปเรื่อยๆ เพื่อไม่ให้บล็อกการรับข้อมูล และทำงานได้ตลอด 24/7
            page.wait_for_timeout(60000) 
    except KeyboardInterrupt:
        print("\n🛑 Shutting down and closing browser...")
        browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        def dummy_callback(data):
            pass
        run(playwright, callback=dummy_callback)