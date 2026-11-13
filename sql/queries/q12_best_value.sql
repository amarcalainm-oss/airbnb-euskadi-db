-- id: Q12
-- author: Iker Elias
-- title: Best-value listings (cheaper than their town, top rated)
-- question: Which well-reviewed listings are cheaper than the median price of their own municipality while keeping a very high value score?
-- why: Comparing each listing with its own municipality and room type (not with the whole region) finds real bargains for a traveller.
-- techniques: CTE with percentile_cont per group, JOIN, correlated subqueries, computed comparison columns
-- params: {"province": null, "room_type": "Entire home/apt", "min_score": 4.8, "min_reviews": 20, "top_n": 20}
WITH town_median AS (
    SELECT municipality_id, room_type,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
           COUNT(*) AS n
    FROM airbnb.listing
    WHERE price IS NOT NULL
    GROUP BY municipality_id, room_type
)
SELECT l.listing_id, l.name AS listing, m.name AS municipality, l.room_type,
       l.price,
       ROUND(tm.median_price::numeric, 2)                       AS town_median_price,
       ROUND(100 * (l.price / tm.median_price::numeric - 1), 1) AS pct_vs_town_median,
       l.score_value, l.score_rating,
       (SELECT COUNT(*) FROM airbnb.listing_review lr WHERE lr.listing_id = l.listing_id) AS n_reviews
FROM airbnb.listing l
JOIN town_median         tm ON tm.municipality_id = l.municipality_id AND tm.room_type = l.room_type
JOIN airbnb.municipality m  ON m.municipality_id  = l.municipality_id
JOIN airbnb.province     p  ON p.province_id      = m.province_id
WHERE l.price < tm.median_price
  AND tm.n >= 10
  AND l.score_value >= %(min_score)s
  AND (SELECT COUNT(*) FROM airbnb.listing_review lr WHERE lr.listing_id = l.listing_id) >= %(min_reviews)s
  AND (%(province)s  IS NULL OR p.name      = %(province)s)
  AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
ORDER BY l.score_value DESC, pct_vs_town_median ASC
LIMIT %(top_n)s;
