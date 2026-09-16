# Chiang Mai National Parks Big Data Mini-project

เว็บแอปสำหรับวิเคราะห์นักท่องเที่ยวอุทยานแห่งชาติภายในจังหวัดเชียงใหม่ โดยรวมข้อมูลท่องเที่ยว สภาพอากาศ PM2.5 และ hotspot รายเดือน ใช้ Python, FastAPI และ Uvicorn ไม่มี Java, Spark หรือ PySpark

## วิธีรัน

ต้องใช้ Python 3.12 ขึ้นไป

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

เปิด Dashboard ที่ `http://127.0.0.1:8000/dashboard` หรือ API documentation ที่ `http://127.0.0.1:8000/docs`

Dashboard ใช้ Sidebar 4 เมนู: Overview, Compare Parks, Trends และ Data Explorer พร้อม Focus mode สำหรับนำเสนอ กราฟรองรับ hover tooltip และดาวน์โหลด CSV ตามตัวกรองได้ ข้อมูล PM2.5/hotspot ยังคงเลือกดูได้จาก Trends

## ขยายข้อมูล Weather

ดาวน์โหลด Open-Meteo แบบรายปีและ resume จาก cache ได้ด้วย:

```bash
python3 fetch_weather_history.py --start-year 2015 --end-year 2025
python3 data_cleaning.py
python3 analytics.py
```

ระบบเก็บ raw response เป็น `cache/weather_YYYY.json` และ aggregate เป็น `data/processed/weather_monthly.csv` ก่อน join เข้ากับ tourism

## Refresh และทดสอบ

ปุ่ม `Refresh data` จะสร้าง processed data และ analytics report จากไฟล์ cache ล่าสุด สามารถทดสอบได้ด้วย:

```bash
python3 -m unittest -v test_project.py
curl http://127.0.0.1:8000/api/summary
curl -X POST http://127.0.0.1:8000/api/refresh
```

## โครงสร้างสำคัญ

- `main.py` — FastAPI routes และ refresh endpoint
- `dashboard.html` — หน้าเว็บ HTML/CSS/JavaScript และ Canvas chart
- `fetch_data.py` — คำสั่งดึงข้อมูลจากแหล่งข้อมูลภายนอก
- `fetch_weather_history.py` — ดาวน์โหลด weather รายปี รองรับ cache และ resume
- `data_cleaning.py` — normalize, filter scope และ join weather
- `analytics.py` — summary, trend, ranking, seasonality และ correlation
- `cache/` — cache/raw response จากแหล่งข้อมูล
- `data/processed/` — dataset พร้อมวิเคราะห์และรายงานคุณภาพ
- `DATA_SOURCE_METADATA.md` — URL, license และข้อจำกัดของแหล่งข้อมูล

## แหล่งข้อมูลและข้อจำกัด

ใช้ DNP/data.go.th สำหรับนักท่องเที่ยว, Open-Meteo Historical API สำหรับอากาศ และ GISTDA/data.go.th สำหรับ PM2.5/hotspot โดย PM2.5 และ hotspot เป็นตัวชี้วัดระดับจังหวัดเชียงใหม่ จึงใช้เปรียบเทียบแนวโน้มระดับจังหวัด ไม่ควรสรุปเป็นค่าภายในอุทยานรายแห่งโดยตรง ข้อมูล NASA FIRMS ไม่ได้ใช้ในโครงงานนี้

Weather ใช้ reference point หนึ่งจุดต่ออุทยาน ไม่ใช่ค่าเฉลี่ยทั้งขอบเขตอุทยาน หาก API ตอบ rate limit สามารถเรียกคำสั่งเดิมซ้ำได้ โดยปีที่ cache สำเร็จแล้วจะไม่ถูกดาวน์โหลดใหม่
