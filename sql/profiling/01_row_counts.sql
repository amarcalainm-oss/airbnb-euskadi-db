-- @query Rows per file
SELECT 'neighbourhoods.csv' AS file, COUNT(*) AS row_count FROM staging.neighbourhoods
UNION ALL SELECT 'listings.csv', COUNT(*) FROM staging.listings
UNION ALL SELECT 'calendar.csv', COUNT(*) FROM staging.calendar
UNION ALL SELECT 'reviews.csv',  COUNT(*) FROM staging.reviews
ORDER BY row_count DESC;

-- @query Columns per file
SELECT table_name AS file, COUNT(*) AS columns
FROM information_schema.columns
WHERE table_schema = 'staging'
GROUP BY table_name
ORDER BY columns DESC;
