-- id: Q02
-- author: Aitor Marcalain
-- title: Most reviewed listings per province (ranking)
-- question: What are the most reviewed listings in each province, and how do they rank within their province?
-- why: The number of reviews is the best public proxy for the number of stays, so the ranking shows which listings capture most of the demand in each province.
-- techniques: CTE, LEFT JOIN, GROUP BY, window function RANK() OVER (PARTITION BY ...)
-- params: {"province": null, "top_n": 5}
WITH review_counts AS (
    -- Step 1: number of reviews of each listing (LEFT JOIN keeps listings with 0 reviews)
    SELECT l.listing_id, l.name AS listing, p.name AS province, m.name AS municipality,
           l.room_type, l.score_rating,
           COUNT(lr.review_id) AS n_reviews
    FROM airbnb.listing l
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    LEFT JOIN airbnb.listing_review lr ON lr.listing_id = l.listing_id
    GROUP BY l.listing_id, p.name, m.name
),
ranked AS (
    -- Step 2: position of each listing inside its province (1 = most reviewed)
    SELECT *, RANK() OVER (PARTITION BY province ORDER BY n_reviews DESC) AS rank_in_province
    FROM review_counts
)
-- Step 3: keep the top N of each province
SELECT province, rank_in_province, listing, municipality, room_type, n_reviews, score_rating
FROM ranked
WHERE rank_in_province <= %(top_n)s
  AND (%(province)s IS NULL OR province = %(province)s)
ORDER BY province, rank_in_province;
