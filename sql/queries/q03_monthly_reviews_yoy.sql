-- id: Q03
-- author: Aitor Marcalain
-- title: Monthly demand trend (reviews per month, year-over-year)
-- question: How has the number of reviews per month evolved, and how does each month compare with the same month of the previous year?
-- why: Reviews are written after a stay, so this curve shows seasonality, the COVID collapse and the recovery of tourist demand in the Basque Country.
-- techniques: CTE chain, generate_series to fill months with no reviews, COUNT(DISTINCT), window function LAG(..., 12)
-- params: {"province": null, "year_from": 2016}
WITH monthly AS (
    -- COUNT(DISTINCT): one review can be linked to several listings of the same host
    SELECT date_trunc('month', r.review_date)::date AS month,
           COUNT(DISTINCT r.review_id)              AS reviews
    FROM airbnb.review r
    JOIN airbnb.listing_review lr ON lr.review_id      = r.review_id
    JOIN airbnb.listing        l  ON l.listing_id      = lr.listing_id
    JOIN airbnb.municipality   m  ON m.municipality_id = l.municipality_id
    JOIN airbnb.province       p  ON p.province_id     = m.province_id
    WHERE (%(province)s IS NULL OR p.name = %(province)s)
    GROUP BY 1
),
all_months AS (
    -- every month between the first and last review, so LAG(12) really means "12 months before"
    SELECT gs::date AS month
    FROM generate_series((SELECT MIN(month) FROM monthly), (SELECT MAX(month) FROM monthly), INTERVAL '1 month') gs
),
series AS (
    SELECT a.month, COALESCE(mo.reviews, 0) AS reviews   -- a month without rows really had 0 reviews
    FROM all_months a LEFT JOIN monthly mo ON mo.month = a.month
),
with_lag AS (
    SELECT month, reviews, LAG(reviews, 12) OVER (ORDER BY month) AS reviews_last_year
    FROM series
)
SELECT month, reviews, reviews_last_year,
       ROUND(100.0 * (reviews - reviews_last_year) / NULLIF(reviews_last_year, 0), 1) AS yoy_change_pct
FROM with_lag
WHERE month >= make_date(%(year_from)s, 1, 1)
ORDER BY month;
