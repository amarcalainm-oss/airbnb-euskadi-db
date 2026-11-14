-- id: Q12
-- author: Iker Elias
-- title: Best-value listings (cheaper than their town, top rated)
-- question: Which well-reviewed listings are cheaper than the median price of their own municipality while keeping a very high value score?
-- why: Comparing each listing with its own municipality and room type (not with the whole region) finds real bargains for a traveller.
-- techniques: two CTEs (median per group with percentile_cont, reviews per listing), JOIN, computed comparison columns
-- params: {"province": null, "room_type": "Entire home/apt", "min_score": 4.8, "min_reviews": 20, "top_n": 20}
WITH town_median AS (
    -- Step 1: median price of each municipality and room type (only groups with 10+ listings)
    SELECT municipality_id, room_type,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY price)::numeric AS median_price
    FROM airbnb.listing
    WHERE price IS NOT NULL
    GROUP BY municipality_id, room_type
    HAVING COUNT(*) >= 10
),
review_counts AS (
    -- Step 2: number of reviews of each listing
    SELECT listing_id, COUNT(*) AS n_reviews
    FROM airbnb.listing_review
    GROUP BY listing_id
)
-- Step 3: listings cheaper than their group's median, with a high value score and enough reviews
SELECT l.listing_id, l.name AS listing, m.name AS municipality, l.room_type,
       l.price,
       ROUND(tm.median_price, 2)                       AS town_median_price,
       ROUND(100 * (l.price / tm.median_price - 1), 1) AS pct_vs_town_median,
       l.score_value, l.score_rating,
       rc.n_reviews
FROM airbnb.listing l
JOIN town_median         tm ON tm.municipality_id = l.municipality_id AND tm.room_type = l.room_type
JOIN review_counts       rc ON rc.listing_id      = l.listing_id
JOIN airbnb.municipality m  ON m.municipality_id  = l.municipality_id
JOIN airbnb.province     p  ON p.province_id      = m.province_id
WHERE l.price < tm.median_price
  AND l.score_value >= %(min_score)s
  AND rc.n_reviews  >= %(min_reviews)s
  AND (%(province)s  IS NULL OR p.name      = %(province)s)
  AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
ORDER BY l.score_value DESC, pct_vs_town_median ASC, l.listing_id   -- listing_id breaks ties: stable order
LIMIT %(top_n)s;
