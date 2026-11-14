-- id: Q10
-- author: Iker Elias
-- title: Repeat guests: how many reviews does each reviewer write?
-- question: How many guests come back and write more than one review in Euskadi, and how many days pass on average between their consecutive reviews?
-- why: The share of repeat guests and the time between visits measure loyalty to the destination, not just to one listing.
-- techniques: CTE, window function LEAD() OVER (PARTITION BY ... ORDER BY ...), GROUP BY, window over an aggregate (SUM(COUNT(*)) OVER ())
-- params: {"year_from": 2011}
WITH rv AS (
    SELECT r.reviewer_id, r.review_date,
           LEAD(r.review_date) OVER (PARTITION BY r.reviewer_id ORDER BY r.review_date, r.review_id) AS next_review_date
    FROM airbnb.review r
    WHERE r.review_date >= make_date(%(year_from)s, 1, 1)
),
per_reviewer AS (
    SELECT reviewer_id, COUNT(*) AS n_reviews, AVG(next_review_date - review_date) AS avg_gap_days
    FROM rv
    GROUP BY reviewer_id
)
SELECT CASE WHEN n_reviews >= 5 THEN '5+' ELSE n_reviews::text END AS reviews_written,
       COUNT(*)                                                 AS reviewers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)        AS pct_reviewers,
       ROUND(AVG(avg_gap_days))                                 AS avg_days_between_reviews
FROM per_reviewer
GROUP BY 1
ORDER BY MIN(n_reviews);
