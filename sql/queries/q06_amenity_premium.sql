-- id: Q06
-- author: Iker Elias
-- title: Price premium of each amenity
-- question: Which amenities are associated with a higher price per guest, comparing listings that have them with those that do not?
-- why: Using price per guest (price / accommodates) removes most of the size effect, so hosts can see which amenities go with higher prices.
-- techniques: CTE chain, JOIN through the N:M bridge table, GROUP BY + HAVING, CROSS JOIN with totals
-- params: {"province": null, "room_type": null, "min_listings": 100, "top_n": 15}
WITH base AS (   -- listings in the filter, with their price per guest
    SELECT l.listing_id, l.price / l.accommodates AS price_per_guest
    FROM airbnb.listing l
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    WHERE l.price IS NOT NULL
      AND (%(province)s  IS NULL OR p.name      = %(province)s)
      AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
),
totals AS (
    SELECT COUNT(*) AS n_all, SUM(price_per_guest) AS sum_all FROM base
),
per_amenity AS (
    SELECT a.name AS amenity, COUNT(*) AS n_with, SUM(b.price_per_guest) AS sum_with
    FROM base b
    JOIN airbnb.listing_amenity la ON la.listing_id = b.listing_id
    JOIN airbnb.amenity         a  ON a.amenity_id  = la.amenity_id
    GROUP BY a.name
    HAVING COUNT(*) >= %(min_listings)s
)
SELECT pa.amenity,
       pa.n_with                                                   AS listings_with,
       t.n_all - pa.n_with                                         AS listings_without,
       ROUND(pa.sum_with / pa.n_with, 2)                           AS avg_price_guest_with,
       ROUND((t.sum_all - pa.sum_with) / (t.n_all - pa.n_with), 2) AS avg_price_guest_without,
       ROUND(100.0 * ((pa.sum_with / pa.n_with) / ((t.sum_all - pa.sum_with) / (t.n_all - pa.n_with)) - 1), 1) AS premium_pct
FROM per_amenity pa CROSS JOIN totals t
WHERE t.n_all - pa.n_with >= %(min_listings)s     -- both groups must be big enough
ORDER BY premium_pct DESC
LIMIT %(top_n)s;
