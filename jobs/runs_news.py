import sys
import os
import json
from supabase import create_client, Client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.newsfetcher import GoldNewsFetcher

# ดึง Config จาก .env
from dotenv import load_dotenv
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def transform_to_flat_list(news_dict: dict) -> list[dict]:
    """
    ฟังก์ชันนี้ทำหน้าที่ 'แกะกล่อง' Nested Dict ของ newsfetcher 
    ให้กลายเป็น List แบบแบนราบ (Flat) เพื่อให้พอดีกับตารางใน PostgreSQL
    """
    flat_articles = []
    
    # วนลูปเข้าไปในแต่ละหมวดหมู่ (เช่น gold_price, fed_policy)
    for category_key, category_data in news_dict.get("by_category", {}).items():
        # วนลูปเอาข่าวแต่ละชิ้นในหมวดหมู่นั้นออกมา
        for article in category_data.get("articles", []):
            
            # จัด Format ข้อมูลให้พร้อมเป็น 1 แถว (Row) ใน Database
            flat_row = {
                "title": article.get("title"),
                "url": article.get("url"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "category": article.get("category"),
                "impact_level": article.get("impact_level"),
                "sentiment_score": article.get("sentiment_score"),
                # คุณสามารถแอบเติมเวลาที่ดึงข้อมูลลงไปเผื่อไว้เช็คย้อนหลังได้ด้วย
                "fetched_at": news_dict.get("fetched_at") 
            }
            flat_articles.append(flat_row)
            
    return flat_articles
    
def main():
    print("🚀 [JOB: NEWS] เริ่มต้นการดึงข่าวและวิเคราะห์ Sentiment...")
    
    fetcher = GoldNewsFetcher(
        max_per_category=3,
        max_total_articles=20,
        token_budget=2000
    )
    
    raw_news_data = fetcher.to_dict()
    print(f"✅ ดึงข่าวสำเร็จ: {raw_news_data['total_articles']} ข่าว")
    
    ready_to_insert_data = transform_to_flat_list(raw_news_data)
    
    # 🌟 ส่วนการส่งข้อมูลเข้า Supabase
    if ready_to_insert_data:
        try:
            print(f"📤 กำลังส่งข้อมูล {len(ready_to_insert_data)} ข่าวเข้า Supabase...")
            # ใช้ .upsert() เพื่อป้องกันการ error เมื่อเจอ URL ซ้ำ (จะอัปเดตแทน)
            response = supabase.table("news_sentiment").upsert(ready_to_insert_data).execute()
            print("✨ บันทึกข่าวลง Database เรียบร้อยแล้ว!")
        except Exception as e:
            print(f"❌ Error บันทึกข่าว: {e}")
    else:
        print("⚠️ ไม่มีข่าวใหม่ที่จะบันทึก")

if __name__ == "__main__":
    main()