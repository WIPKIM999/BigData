# Canonical Data Schema

เวอร์ชัน schema: `1.0`

เป้าหมายของ schema นี้คือทำให้ข้อมูลจาก CSV และ Public API หลายแหล่งสามารถรวมและวิเคราะห์ร่วมกันได้ โดยไม่ผูกกับฐานข้อมูลชนิดใดชนิดหนึ่ง

## 1. Common conventions

- ชื่อ field ใช้ `snake_case` ภาษาอังกฤษ
- ข้อมูลข้อความใช้ UTF-8
- วันที่ใช้ ISO 8601 เช่น `2024-01-31`
- timestamp ใช้ ISO 8601 พร้อม timezone เช่น `2024-01-31T13:00:00+07:00`
- เวลาในระบบใช้ `Asia/Bangkok`; เวลาจาก API ที่เป็น UTC ต้องแปลงก่อน join
- จำนวนและค่าการวัดเป็นตัวเลข ไม่เก็บ comma หรือหน่วยไว้ในค่า
- ค่าว่างใช้ `null` ไม่ใช้ `-`, `ไม่มีข้อมูล` หรือ `N/A`
- ทุก record ต้องมี `source_name`, `retrieved_at` และ `schema_version`

## 2. Park dimension

ไฟล์: `data/processed/parks.json`

| Field | Type | Required | Description |
|---|---|---:|---|
| `park_id` | string | yes | รหัสภายในระบบ เช่น `doi_inthanon` |
| `park_name` | string | yes | ชื่ออุทยานมาตรฐาน |
| `province` | string | yes | ต้องเป็น `เชียงใหม่` |
| `latitude` | number | yes | จุดอ้างอิงสำหรับ weather API |
| `longitude` | number | yes | จุดอ้างอิงสำหรับ weather API |
| `scope_note` | string/null | no | หมายเหตุกรณีพื้นที่คาบเกี่ยวจังหวัด |

## 3. Tourism fact

ไฟล์: `data/processed/tourism.csv`

หนึ่ง record แทนจำนวนผู้เข้าชมของหนึ่งอุทยานในหนึ่งเดือนและหนึ่งปีงบประมาณ

| Field | Type | Required | Description |
|---|---|---:|---|
| `park_id` | string | yes | join กับ park dimension |
| `park_name` | string | yes | ชื่อมาตรฐานเพื่ออ่านง่าย |
| `province` | string | yes | `เชียงใหม่` |
| `fiscal_year` | integer | yes | ปีงบประมาณ พ.ศ. ตามต้นทาง |
| `calendar_year` | integer/null | no | ปี ค.ศ. หลังแปลง ถ้าระบุเดือนที่แปลงได้ |
| `month` | integer | yes | 1–12 |
| `thai_visitors` | integer/null | no | นักท่องเที่ยวชาวไทย |
| `foreign_visitors` | integer/null | no | นักท่องเที่ยวชาวต่างชาติ |
| `total_visitors` | integer/null | no | ยอดรวมจากต้นทางหรือผลรวมที่ตรวจสอบแล้ว |
| `source_name` | string | yes | แหล่งข้อมูลต้นทาง |
| `source_url` | string | yes | URL ของ resource ที่ใช้ |
| `retrieved_at` | timestamp | yes | เวลาที่ดึงข้อมูล |
| `schema_version` | string | yes | `1.0` |

Natural key: `park_id + fiscal_year + month + source_name`

## 4. Weather fact

ไฟล์: `data/processed/weather_hourly.csv`

หนึ่ง record แทนข้อมูลอากาศของหนึ่งอุทยานในหนึ่งชั่วโมง โดยใช้ค่าจาก reference point ของอุทยาน

| Field | Type | Required | Description |
|---|---|---:|---|
| `park_id` | string | yes | join กับ park dimension |
| `timestamp` | timestamp | yes | เวลา local `Asia/Bangkok` |
| `temperature_2m_c` | number/null | no | อุณหภูมิองศาเซลเซียส |
| `relative_humidity_pct` | number/null | no | ความชื้นสัมพัทธ์ |
| `precipitation_mm` | number/null | no | ปริมาณฝน |
| `wind_speed_10m_kmh` | number/null | no | ความเร็วลม |
| `weather_code` | integer/null | no | WMO weather interpretation code |
| `source_name` | string | yes | `open_meteo` |
| `source_url` | string | yes | URL ที่ใช้ query |
| `retrieved_at` | timestamp | yes | เวลาที่ดึงข้อมูล |
| `schema_version` | string | yes | `1.0` |

Natural key: `park_id + timestamp + source_name`

## 5. Hotspot fact

ไฟล์: `data/processed/hotspots.csv`

รองรับทั้งข้อมูลแบบรายจุดและข้อมูลสรุปรายวันจาก GISTDA/data.go.th เพราะรายละเอียด field ของแต่ละ resource อาจต่างกัน

| Field | Type | Required | Description |
|---|---|---:|---|
| `park_id` | string/null | no | เติมหลัง spatial filtering ถ้าจุดอยู่ในอุทยาน |
| `record_date` | date | yes | วันที่ตรวจพบหรือวันที่สรุป |
| `latitude` | number/null | no | พิกัดละติจูด ถ้าต้นทางมี |
| `longitude` | number/null | no | พิกัดลองจิจูด ถ้าต้นทางมี |
| `hotspot_count` | integer | yes | จำนวนจุดความร้อนของ record |
| `land_use_type` | string/null | no | ประเภทพื้นที่ถ้ามี |
| `source_name` | string | yes | `gistda_chiang_mai` หรือชื่อ resource |
| `source_url` | string | yes | URL ของ resource ที่ใช้ |
| `retrieved_at` | timestamp | yes | เวลาที่ดึงข้อมูล |
| `schema_version` | string | yes | `1.0` |

Natural key: `source_name + record_date + latitude + longitude + land_use_type`

## 6. Air quality fact

ไฟล์: `data/processed/air_quality.csv`

| Field | Type | Required | Description |
|---|---|---:|---|
| `station_id` | string | yes | รหัสสถานีจากต้นทาง |
| `station_name` | string/null | no | ชื่อสถานี |
| `timestamp` | timestamp | yes | เวลาการวัด |
| `latitude` | number/null | no | พิกัดสถานี |
| `longitude` | number/null | no | พิกัดสถานี |
| `pm25_ug_m3` | number/null | no | PM2.5 |
| `pm10_ug_m3` | number/null | no | PM10 |
| `park_id` | string/null | no | อุทยานที่ใกล้หรือครอบคลุมหลัง spatial join |
| `source_name` | string | yes | ชื่อแหล่งข้อมูล |
| `source_url` | string | yes | URL ของ API/resource |
| `retrieved_at` | timestamp | yes | เวลาที่ดึงข้อมูล |
| `schema_version` | string | yes | `1.0` |

## 7. Join strategy

### Tourism + Weather

1. Aggregate `weather_hourly` เป็น `park_id + calendar_year + month`
2. คำนวณ `avg_temperature`, `sum_precipitation`, `avg_humidity` และ `avg_wind_speed`
3. Join กับ tourism ด้วย `park_id + calendar_year + month`

### Tourism + Hotspot

1. Aggregate hotspot เป็น `park_id + calendar_year + month` ถ้ามีพิกัดอุทยาน
2. หากเป็นข้อมูลระดับจังหวัด ให้ใช้ `province + calendar_year + month` และระบุว่าเป็น provincial indicator
3. ห้ามตีความข้อมูลระดับจังหวัดว่าเป็นค่าภายในอุทยานโดยตรง

### Tourism + Air quality

1. Aggregate air quality เป็นรายวันหรือรายเดือน
2. จับคู่สถานีกับอุทยานด้วยพิกัดหรือเลือกสถานีตัวแทนที่ใกล้ที่สุด
3. เก็บ `station_id` และระยะทางไว้เพื่ออธิบายข้อจำกัดของการประมาณค่า

## 8. Quality rules

- `park_id` ต้องอยู่ใน `park_coordinates.json`
- `province` ต้องเท่ากับ `เชียงใหม่` สำหรับข้อมูลที่อยู่ใน scope
- `month` ต้องอยู่ระหว่าง 1 ถึง 12
- `total_visitors`, `hotspot_count` และ count ต่าง ๆ ต้องไม่ติดลบ
- latitude ต้องอยู่ระหว่าง -90 ถึง 90 และ longitude ระหว่าง -180 ถึง 180
- weather timestamp ต้องไม่ซ้ำกันภายใน natural key
- ตรวจสอบผลรวมรายเดือนกับยอดจาก source ก่อนนำเข้า Dashboard
