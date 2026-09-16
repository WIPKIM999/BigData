# Hotspot Scope Decision

NASA FIRMS is not used in this project. The selected GISTDA/data.go.th hotspot source is retained as a province-level environmental indicator because the available resource is an aggregate for Chiang Mai and does not provide one coordinate per hotspot.

Rules:

- Keep Chiang Mai aggregate hotspot rows with `geography_level=province`.
- Keep `park_id=null` for aggregate rows.
- Do not claim that a provincial count belongs to a specific park.
- If a future source provides latitude/longitude, apply the Chiang Mai bounding-box filter first, then assign `park_id` only after obtaining park polygon geometry.

Implementation: `hotspot_scope.py`
