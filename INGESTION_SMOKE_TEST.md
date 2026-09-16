# Ingestion Smoke Test

วันที่ทดสอบ: 16 กันยายน 2569

| Source | Test | Result |
|---|---|---|
| Open-Meteo | 11 reference points, 1–7 January 2016 | สำเร็จ: 1,848 hourly records |
| data.go.th Tourism catalog | Discover resources | สำเร็จ: พบ 39 resources และ CSV แยกรายปี/รวมปี 2559–2568 |
| DNP Tourism CSV | Download and profile rows | สำเร็จ: 1,543 rows, 14 columns, no blank cells in source columns |
| Chiang Mai hotspot catalog | Discover resources | สำเร็จ: พบ 2 resources |
| Chiang Mai rainfall catalog | Discover resources | สำเร็จ: พบ 1 resource |
| OpenAQ | Verify API documentation and access model | สำเร็จในระดับ API contract; ต้องเลือกสถานีจริงก่อนดึงข้อมูล |

## Current evidence

- Weather raw response: `cache/weather_2016-01-01_2016-01-07.json`
- Weather metadata: `cache/weather_2016-01-01_2016-01-07.metadata.json`
- Tourism catalog manifest: `cache/tourism_resources.json`
- Tourism raw CSV: `cache/tourism59-68.csv`
- Tourism metadata/profile: `cache/tourism59-68.metadata.json`

## Tourism profile result

- Source coverage: fiscal years 2559–2568
- Full source: 1,543 rows
- Records with affiliation containing `16`: 198 rows
- Source layout: wide monthly columns from `ต.ค.` through `ก.ย.`; this must be unpivoted before canonical monthly analysis
- Important: affiliation 16 also contains non-scope/proposed parks, so the canonical park-name filter in `PROJECT_SCOPE.md` must be applied before joining

## Pending action

The first download attempt timed out, but a subsequent retry succeeded. The selected CSV has now been profiled; continue with name normalization and scope filtering in Step 5.
