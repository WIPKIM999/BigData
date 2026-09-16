# รายงานผลลัพธ์เบื้องต้น

## Methodology

กรองข้อมูลเฉพาะอุทยาน 11 แห่งในจังหวัดเชียงใหม่ แปลงปีงบประมาณและชื่อเดือนเป็นปี/เดือนมาตรฐาน จากนั้น aggregate weather รายเดือนต่ออุทยาน แล้ว join กับ tourism ด้วย `park_id + calendar_year + month` ส่วน PM2.5 และ hotspot เป็นข้อมูลระดับจังหวัด จึง aggregate นักท่องเที่ยวทุกอุทยานต่อเดือนก่อนคำนวณ correlation

## Dataset profile

| Dataset | Records | หมายเหตุ |
|---|---:|---|
| Tourism source | 1,543 | CSV จาก DNP/data.go.th |
| Tourism หลังกรอง scope | 1,296 | 11 อุทยาน |
| Weather historical cache | 1,060,752 | 11 จุดอ้างอิง × ปี 2015–2025 |
| Environment indicators | 25 เดือน | PM2.5 และ hotspot ช่วง 2563–2567 |
| Combined environment dataset | 1,296 | tourism + weather + environment |

Weather ถูก aggregate เป็น 1,452 park-month records และจับคู่กับ tourism ได้ครบ 1,296 records ช่วงปี 2015–2025

## ข้อค้นพบ

- นักท่องเที่ยวรวม `14,307,746` คน จาก 11 อุทยาน
- อุทยานที่มียอดสูงสุดคือ ดอยอินทนนท์ `5,978,442` คน
- ฤดูหนาวมียอดรวมสูงสุด รองลงมาคือฤดูฝนและฤดูร้อน
- Pearson correlation ระหว่างยอดรวมรายเดือนกับ PM2.5 สูงสุดอยู่ที่ `-0.1210`, จำนวนวันที่เกินมาตรฐาน `-0.0862` และ hotspot `-0.1280`

ค่า correlation เป็นเพียงความสัมพันธ์เชิงสำรวจ ไม่ใช่เหตุและผล และมีข้อจำกัดจากข้อมูล environment ระดับจังหวัดและจำนวนเดือนที่ใช้ 25 เดือน

## Benchmark

รอบล่าสุดใช้เวลาประมาณ `0.046` วินาที และใช้หน่วยความจำสูงสุดประมาณ `2.30 MB` บนเครื่องพัฒนา ค่า benchmark ใช้เพื่อเปรียบเทียบ pipeline รุ่นเดียวกัน ไม่ใช่ผลแทน production scale
