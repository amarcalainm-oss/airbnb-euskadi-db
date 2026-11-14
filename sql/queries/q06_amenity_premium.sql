-- id: Q06
-- author: Iker Elias
-- title: Price premium of each amenity
-- question: Which amenities are associated with a higher price per guest, comparing listings that have them with those that do not?
-- why: Using price per guest (price / accommodates) removes most of the size effect, so hosts can see which amenities go with higher prices.
-- techniques: CTE chain, JOIN through the N:M bridge table, GROUP BY + HAVING, CROSS JOIN with totals
-- params: {"province": null, "room_type": null, "min_listings": 100, "top_n": 15}
WITH base AS (
    -- Step 1: listings in the filter, with their price per guest
    SELECT l.listing_id, l.price / l.accommodates AS price_per_guest
    FROM airbnb.listing l
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    WHERE l.price IS NOT NULL
      AND (%(province)s  IS NULL OR p.name      = %(province)s)
      AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
),
overall AS (
    -- Step 2: one row with the totals of ALL listings in the filter
    SELECT COUNT(*) AS n_all, SUM(price_per_guest) AS sum_all
    FROM base
),
with_amenity AS (
    -- Step 3: for each amenity, the listings that HAVE it (through the bridge table)
    SELECT a.name AS amenity, COUNT(*) AS n_with, SUM(b.price_per_guest) AS sum_with
    FROM base b
    JOIN airbnb.listing_amenity la ON la.listing_id = b.listing_id
    JOIN airbnb.amenity         a  ON a.amenity_id  = la.amenity_id
    GROUP BY a.name
    HAVING COUNT(*) >= %(min_listings)s
),
both_groups AS (
    -- Step 4: the listings WITHOUT the amenity are "all minus those with it"
    SELECT w.amenity,
           w.n_with,
           o.n_all - w.n_with                                       AS n_without,
           w.sum_with / w.n_with                                    AS avg_with,
           (o.sum_all - w.sum_with) / NULLIF(o.n_all - w.n_with, 0) AS avg_without
    FROM with_amenity w CROSS JOIN overall o
)
-- Step 5: compare the two averages; both groups must be big enough
SELECT amenity,
       n_with                                   AS listings_with,
       n_without                                AS listings_without,
       ROUND(avg_with, 2)                       AS avg_price_guest_with,
       ROUND(avg_without, 2)                    AS avg_price_guest_without,
       ROUND(100.0 * (avg_with / avg_without - 1), 1) AS premium_pct
FROM both_groups
WHERE n_without >= %(min_listings)s
ORDER BY premium_pct DESC
LIMIT %(top_n)s;
