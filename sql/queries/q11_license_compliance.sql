-- id: Q11
-- author: Aitor Marcalain
-- title: Tourist-registry licence status by municipality
-- question: In which municipalities is the share of listings without any registration number highest?
-- why: Basque law requires tourist flats to show a registration number, so listings without one point to where regulation is least enforced.
-- techniques: JOIN, GROUP BY + HAVING, aggregate FILTER, pattern matching (ILIKE)
-- params: {"province": null, "room_type": null, "min_listings": 20, "top_n": 15}
SELECT m.name                                                              AS municipality,
       p.name                                                              AS province,
       COUNT(*)                                                            AS listings,
       COUNT(*) FILTER (WHERE l.license IS NOT NULL AND l.license NOT ILIKE '%%exempt%%') AS registered,
       COUNT(*) FILTER (WHERE l.license ILIKE '%%exempt%%')                AS exempt,
       COUNT(*) FILTER (WHERE l.license IS NULL)                           AS no_license,
       ROUND(100.0 * COUNT(*) FILTER (WHERE l.license IS NULL) / COUNT(*), 1) AS pct_no_license
FROM airbnb.listing l
JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
JOIN airbnb.province     p ON p.province_id     = m.province_id
WHERE (%(province)s  IS NULL OR p.name      = %(province)s)
  AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
GROUP BY m.name, p.name
HAVING COUNT(*) >= %(min_listings)s
ORDER BY pct_no_license DESC, listings DESC
LIMIT %(top_n)s;
