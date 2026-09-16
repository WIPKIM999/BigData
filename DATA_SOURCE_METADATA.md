# Data Source Metadata

อัปเดตล่าสุด: 16 กันยายน 2569

## Required sources

| Source | Provider | Access | Frequency | Scope/filter | Status |
|---|---|---|---|---|---|
| Tourism statistics | กรมอุทยานฯ / data.go.th | CKAN package API + CSV resources | รายเดือน/รายปี | กรองชื่ออุทยานใน `PROJECT_SCOPE.md` | Download/profile verified |
| Historical weather | Open-Meteo | REST JSON API | รายชั่วโมง | เรียกจาก reference point ของ 11 อุทยาน | Smoke test verified |
| Hotspots | GISTDA / สำนักงานจังหวัดเชียงใหม่ | data.go.th CSV/XLSX resources | รายเดือน/รายปีตามชุดข้อมูล | กรองเฉพาะเชียงใหม่และเชื่อมกับอุทยาน | Catalog identified |

## Optional sources

| Source | Provider | Access | Frequency | Purpose | Status |
|---|---|---|---|---|---|
| PM2.5/hotspot/rainfall | สำนักงานจังหวัดเชียงใหม่ / data.go.th | Public catalog resources | รายเดือน/รายปีตามชุดข้อมูล | ตรวจสอบเทียบและเพิ่มตัวแปรสิ่งแวดล้อม | Catalog identified |
| Air quality | OpenAQ | REST JSON API v3 | รายชั่วโมง/รายวัน | เพิ่ม PM2.5/PM10 จากสถานีที่ครอบคลุมพื้นที่ | API documented; station check pending |

## Verified tourism catalog result

The data.go.th package discovery request returned 39 resources, including a combined CSV resource covering fiscal years 2559–2568 and separate yearly CSV/XLSX resources. The ingestion code stores the returned resource manifest in `cache/tourism_resources.json` so the selected download URL is traceable.

## API and license notes

- Tourism data: use the license and access conditions returned in the data.go.th resource metadata; retain the source URL and retrieval timestamp.
- Open-Meteo: retain attribution and record that historical values are reanalysis/model data.
- OpenAQ: API v3 uses the `X-API-Key` header for historical measurement endpoints; verify applicable upstream terms before publication.

## Retrieval metadata to store for every run

```text
source_name
request_url
retrieved_at_utc
start_date
end_date
http_status
response_format
row_count
sha256
error_message
```
