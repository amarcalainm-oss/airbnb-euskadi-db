-- id: Q08
-- author: Iker Elias
-- title: Weekend vs weekday unavailability by municipality
-- question: In which municipalities are Friday and Saturday nights unavailable (booked or blocked by the host) much more often than weekday nights over the coming weeks?
-- why: A large weekend gap marks short-break destinations (city/beach getaways), while a small gap suggests longer holiday or business stays.
-- techniques: CTE, scalar subquery, aggregate FILTER, EXTRACT(ISODOW), GROUP BY + HAVING, window function RANK()
-- params: {"province": null, "horizon_days": 90, "min_listings": 30, "top_n": 15}
WITH nights AS (
    SELECT m.name AS municipality, p.name AS province, c.listing_id,
           EXTRACT(ISODOW FROM c.day) IN (5, 6) AS is_weekend,
           NOT c.available                      AS is_unavailable
    FROM airbnb.calendar_day c
    JOIN airbnb.listing      l ON l.listing_id      = c.listing_id
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    WHERE c.day < (SELECT MIN(day) FROM airbnb.calendar_day) + %(horizon_days)s
      AND (%(province)s IS NULL OR p.name = %(province)s)
),
occ AS (
    SELECT municipality, province,
           COUNT(DISTINCT listing_id) AS listings,
           100.0 * COUNT(*) FILTER (WHERE is_weekend AND is_unavailable)
                 / COUNT(*) FILTER (WHERE is_weekend)                 AS weekend_occ,
           100.0 * COUNT(*) FILTER (WHERE NOT is_weekend AND is_unavailable)
                 / COUNT(*) FILTER (WHERE NOT is_weekend)             AS weekday_occ
    FROM nights
    GROUP BY municipality, province
    HAVING COUNT(DISTINCT listing_id) >= %(min_listings)s
)
SELECT RANK() OVER (ORDER BY weekend_occ - weekday_occ DESC) AS rank,
       municipality, province, listings,
       ROUND(weekend_occ, 1)               AS weekend_occ_pct,
       ROUND(weekday_occ, 1)               AS weekday_occ_pct,
       ROUND(weekend_occ - weekday_occ, 1) AS gap_points
FROM occ
ORDER BY rank
LIMIT %(top_n)s;
