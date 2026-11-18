-- @query Format and range of dates
SELECT 'listings.last_scraped' AS column_name,
       COUNT(*) FILTER (WHERE last_scraped !~ '^\d{4}-\d{2}-\d{2}$') AS bad_format,
       MIN(last_scraped::date) AS min_value, MAX(last_scraped::date) AS max_value FROM staging.listings
UNION ALL
SELECT 'listings.host_since',
       COUNT(*) FILTER (WHERE host_since !~ '^\d{4}-\d{2}-\d{2}$'),
       MIN(host_since::date), MAX(host_since::date) FROM staging.listings
UNION ALL
SELECT 'listings.first_review',
       COUNT(*) FILTER (WHERE first_review !~ '^\d{4}-\d{2}-\d{2}$'),
       MIN(first_review::date), MAX(first_review::date) FROM staging.listings
UNION ALL
SELECT 'listings.last_review',
       COUNT(*) FILTER (WHERE last_review !~ '^\d{4}-\d{2}-\d{2}$'),
       MIN(last_review::date), MAX(last_review::date) FROM staging.listings
UNION ALL
SELECT 'calendar.date',
       COUNT(*) FILTER (WHERE date !~ '^\d{4}-\d{2}-\d{2}$'),
       MIN(date::date), MAX(date::date) FROM staging.calendar
UNION ALL
SELECT 'reviews.date',
       COUNT(*) FILTER (WHERE date !~ '^\d{4}-\d{2}-\d{2}$'),
       MIN(date::date), MAX(date::date) FROM staging.reviews;

-- @query Price format (text with a $ sign and thousands separators)
SELECT CASE
         WHEN price IS NULL OR price = ''           THEN '(empty)'
         WHEN price ~ '^\$\d{1,3}(,\d{3})*\.\d{2}$' THEN '$#,###.## (valid)'
         ELSE 'other format'
       END AS format,
       COUNT(*) AS row_count,
       MIN(price) AS example
FROM staging.listings
GROUP BY 1 ORDER BY row_count DESC;

-- @query Numeric ranges in listings
SELECT 'price ($)' AS column_name,
       MIN(replace(substr(price, 2), ',', '')::numeric) AS min_value,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY replace(substr(price, 2), ',', '')::numeric) AS median,
       MAX(replace(substr(price, 2), ',', '')::numeric) AS max_value
FROM staging.listings WHERE price <> ''
UNION ALL SELECT 'latitude', MIN(latitude::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY latitude::numeric), MAX(latitude::numeric) FROM staging.listings
UNION ALL SELECT 'longitude', MIN(longitude::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY longitude::numeric), MAX(longitude::numeric) FROM staging.listings
UNION ALL SELECT 'accommodates', MIN(accommodates::int), percentile_cont(0.5) WITHIN GROUP (ORDER BY accommodates::int), MAX(accommodates::int) FROM staging.listings
UNION ALL SELECT 'bedrooms', MIN(bedrooms::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY bedrooms::numeric), MAX(bedrooms::numeric) FROM staging.listings
UNION ALL SELECT 'beds', MIN(beds::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY beds::numeric), MAX(beds::numeric) FROM staging.listings
UNION ALL SELECT 'bathrooms', MIN(bathrooms::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY bathrooms::numeric), MAX(bathrooms::numeric) FROM staging.listings
UNION ALL SELECT 'minimum_nights', MIN(minimum_nights::int), percentile_cont(0.5) WITHIN GROUP (ORDER BY minimum_nights::int), MAX(minimum_nights::int) FROM staging.listings
UNION ALL SELECT 'maximum_nights', MIN(maximum_nights::bigint), percentile_cont(0.5) WITHIN GROUP (ORDER BY maximum_nights::bigint), MAX(maximum_nights::bigint) FROM staging.listings
UNION ALL SELECT 'availability_365', MIN(availability_365::int), percentile_cont(0.5) WITHIN GROUP (ORDER BY availability_365::int), MAX(availability_365::int) FROM staging.listings
UNION ALL SELECT 'number_of_reviews', MIN(number_of_reviews::int), percentile_cont(0.5) WITHIN GROUP (ORDER BY number_of_reviews::int), MAX(number_of_reviews::int) FROM staging.listings
UNION ALL SELECT 'review_scores_rating', MIN(review_scores_rating::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY review_scores_rating::numeric), MAX(review_scores_rating::numeric) FROM staging.listings
UNION ALL SELECT 'estimated_revenue_l365d', MIN(estimated_revenue_l365d::numeric), percentile_cont(0.5) WITHIN GROUP (ORDER BY estimated_revenue_l365d::numeric), MAX(estimated_revenue_l365d::numeric) FROM staging.listings
UNION ALL SELECT 'host_listings_count', MIN(host_listings_count::int), percentile_cont(0.5) WITHIN GROUP (ORDER BY host_listings_count::int), MAX(host_listings_count::int) FROM staging.listings;

-- @query Numeric ranges in calendar
SELECT 'minimum_nights' AS column_name, MIN(minimum_nights::bigint) AS min_value, MAX(minimum_nights::bigint) AS max_value FROM staging.calendar
UNION ALL SELECT 'maximum_nights', MIN(maximum_nights::bigint), MAX(maximum_nights::bigint) FROM staging.calendar;

-- @query Format of the host percentage columns
SELECT 'host_response_rate' AS column_name, COUNT(*) FILTER (WHERE host_response_rate ~ '^\d{1,3}%$') AS format_nn_pct,
       COUNT(*) FILTER (WHERE host_response_rate IN ('N/A')) AS value_na,
       COUNT(*) FILTER (WHERE host_response_rate IS NULL OR host_response_rate = '') AS empty
FROM staging.listings
UNION ALL
SELECT 'host_acceptance_rate', COUNT(*) FILTER (WHERE host_acceptance_rate ~ '^\d{1,3}%$'),
       COUNT(*) FILTER (WHERE host_acceptance_rate IN ('N/A')),
       COUNT(*) FILTER (WHERE host_acceptance_rate IS NULL OR host_acceptance_rate = '')
FROM staging.listings;

-- @query Values of the boolean columns ('t' / 'f' expected)
SELECT 'listings.host_is_superhost' AS column_name, host_is_superhost AS value, COUNT(*) AS row_count FROM staging.listings GROUP BY 2
UNION ALL SELECT 'listings.host_identity_verified', host_identity_verified, COUNT(*) FROM staging.listings GROUP BY 2
UNION ALL SELECT 'listings.host_has_profile_pic', host_has_profile_pic, COUNT(*) FROM staging.listings GROUP BY 2
UNION ALL SELECT 'listings.has_availability', has_availability, COUNT(*) FROM staging.listings GROUP BY 2
UNION ALL SELECT 'listings.instant_bookable', instant_bookable, COUNT(*) FROM staging.listings GROUP BY 2
UNION ALL SELECT 'calendar.available', available, COUNT(*) FROM staging.calendar GROUP BY 2
ORDER BY 1, 2;
