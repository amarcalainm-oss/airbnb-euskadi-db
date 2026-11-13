-- id: Q09
-- author: Aitor Marcalain
-- title: What-if: price change in a municipality (UPDATE inside a transaction)
-- question: If every listing in a municipality changed its price by X %, how would the municipality's average and median price change?
-- why: It runs a real UPDATE inside a transaction, measures the effect and then ROLLBACKs, so the database is never left modified: a safe "simulation" mode.
-- techniques: transaction (BEGIN ... ROLLBACK), UPDATE ... FROM with a join, aggregates before/after
-- params: {"municipality": "Donostia-San Sebastián", "pct_change": 10}
-- type: transaction
-- @step before
SELECT 'before' AS moment, COUNT(l.price) AS listings_with_price,
       ROUND(AVG(l.price), 2) AS avg_price,
       ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price)::numeric, 2) AS median_price
FROM airbnb.listing l JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
WHERE m.name = %(municipality)s;
-- @step update
UPDATE airbnb.listing l
SET price = ROUND(l.price * (1 + %(pct_change)s / 100.0), 2)
FROM airbnb.municipality m
WHERE m.municipality_id = l.municipality_id
  AND m.name = %(municipality)s
  AND l.price IS NOT NULL;
-- @step after
SELECT 'after' AS moment, COUNT(l.price) AS listings_with_price,
       ROUND(AVG(l.price), 2) AS avg_price,
       ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price)::numeric, 2) AS median_price
FROM airbnb.listing l JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
WHERE m.name = %(municipality)s;
