-- id: Q05
-- author: Iker Elias
-- title: Booked/blocked days per month for the next year
-- question: For the next 12 months, what percentage of listing-days are already unavailable in each province?
-- why: An unavailable day is either booked or blocked by the host, so this curve shows the expected busy seasons (summer, holidays) months in advance.
-- techniques: CTE, JOIN on the 2.3 M-row calendar table, GROUP BY, aggregate FILTER
-- params: {"room_type": null}
WITH days AS (
    SELECT date_trunc('month', c.day)::date AS month, p.name AS province, c.available
    FROM airbnb.calendar_day c
    JOIN airbnb.listing      l ON l.listing_id      = c.listing_id
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    WHERE (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
)
SELECT month, province,
       COUNT(*)                                                           AS listing_days,
       ROUND(100.0 * COUNT(*) FILTER (WHERE NOT available) / COUNT(*), 1) AS pct_unavailable
FROM days
GROUP BY month, province
ORDER BY month, province;
