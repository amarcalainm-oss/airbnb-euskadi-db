-- id: Q01
-- author: Aitor Marcalain
-- title: Nightly price by municipality
-- question: Which municipalities are the most expensive per night, considering only municipalities with enough listings to be representative?
-- why: The median (not the mean) is robust to luxury outliers, and HAVING removes towns with 2-3 listings whose price says nothing about the market.
-- techniques: JOIN of 3 tables, GROUP BY + HAVING, ordered-set aggregate (percentile_cont)
-- params: {"province": null, "room_type": null, "min_listings": 20, "top_n": 15}
SELECT m.name                                     AS municipality,
       p.name                                     AS province,
       COUNT(*)                                   AS listings,
       ROUND(AVG(l.price), 2)                     AS avg_price,
       ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price)::numeric, 2) AS median_price
FROM airbnb.listing l
JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
JOIN airbnb.province     p ON p.province_id     = m.province_id
WHERE l.price IS NOT NULL
  AND (%(province)s  IS NULL OR p.name      = %(province)s)
  AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
GROUP BY m.name, p.name
HAVING COUNT(*) >= %(min_listings)s
ORDER BY median_price DESC
LIMIT %(top_n)s;
