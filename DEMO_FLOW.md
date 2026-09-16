# Demo flow

1. รัน `uvicorn main:app --reload`
2. เปิด `/dashboard` และตรวจ KPI/กราฟจากข้อมูลจริง
3. เลือกปี เดือน หรืออุทยานเพื่อสาธิต filter ผ่าน API โดยไม่ reload ทั้งหน้า
4. กด `Refresh data` เพื่อสร้าง processed data และ analytics report ใหม่จาก cache
5. เปิด `/docs` เพื่อแสดง Swagger และเรียก `/api/summary`, `/api/environment`
6. อธิบาย insight จาก `RESULTS_REPORT.md` พร้อมระบุว่า PM2.5/hotspot เป็นตัวชี้วัดระดับจังหวัด
7. หากต้องการ export ให้ดาวน์โหลด `data/processed/combined_environment_monthly.csv`
