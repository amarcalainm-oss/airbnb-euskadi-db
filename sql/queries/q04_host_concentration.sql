-- id: Q04
-- author: Aitor Marcalain
-- title: Multi-listing hosts (market concentration)
-- question: Which hosts manage the most listings, and what share of the whole supply does each of them control?
-- why: A few professional operators holding a large share of listings is a key argument in the debate about tourist flats and housing.
-- techniques: JOIN, GROUP BY + HAVING, scalar subquery in SELECT
-- params: {"province": null, "min_listings": 10, "top_n": 15}
SELECT h.host_id,
       h.name                              AS host,
       h.is_superhost,
       COUNT(*)                            AS listings,
       -- scalar subquery: total listings in the filter, to turn the count into a share
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*)
                                 FROM airbnb.listing l2
                                 JOIN airbnb.municipality m2 ON m2.municipality_id = l2.municipality_id
                                 JOIN airbnb.province     p2 ON p2.province_id     = m2.province_id
                                 WHERE %(province)s IS NULL OR p2.name = %(province)s), 2) AS pct_of_supply,
       COUNT(DISTINCT l.municipality_id)  AS municipalities,
       ROUND(AVG(l.price), 2)             AS avg_price
FROM airbnb.listing l
JOIN airbnb.host         h ON h.host_id         = l.host_id
JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
JOIN airbnb.province     p ON p.province_id     = m.province_id
WHERE (%(province)s IS NULL OR p.name = %(province)s)
GROUP BY h.host_id
HAVING COUNT(*) >= %(min_listings)s
ORDER BY listings DESC
LIMIT %(top_n)s;
