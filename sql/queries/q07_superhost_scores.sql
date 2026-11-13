-- id: Q07
-- author: Iker Elias
-- title: Superhosts vs regular hosts
-- question: Do listings run by superhosts really get better guest scores than those of regular hosts, in each province?
-- why: It checks whether the "Superhost" badge reflects a measurable difference in guest satisfaction and price, using only listings with enough reviews.
-- techniques: JOIN, GROUP BY, correlated subquery in WHERE, CASE
-- params: {"min_reviews": 10}
SELECT p.name                                                            AS province,
       CASE WHEN h.is_superhost THEN 'Superhost' ELSE 'Regular host' END AS host_type,
       COUNT(*)                                                          AS listings,
       ROUND(AVG(l.score_rating), 3)                                     AS avg_rating,
       ROUND(AVG(l.score_cleanliness), 3)                                AS avg_cleanliness,
       ROUND(AVG(l.score_communication), 3)                              AS avg_communication,
       ROUND(AVG(l.score_value), 3)                                      AS avg_value,
       ROUND(AVG(l.price), 2)                                            AS avg_price
FROM airbnb.listing l
JOIN airbnb.host         h ON h.host_id         = l.host_id
JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
JOIN airbnb.province     p ON p.province_id     = m.province_id
WHERE l.score_rating IS NOT NULL
  AND (SELECT COUNT(*) FROM airbnb.listing_review lr WHERE lr.listing_id = l.listing_id) >= %(min_reviews)s
GROUP BY p.name, h.is_superhost
ORDER BY province, host_type DESC;
