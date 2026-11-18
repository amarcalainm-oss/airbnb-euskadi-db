-- @query Double-encoded text (mojibake: 'ú' stored as 'Ãº', 'Á' as 'Ã' plus a control character)
SELECT 'neighbourhoods.neighbourhood_group' AS column_name, COUNT(*) FILTER (WHERE neighbourhood_group LIKE '%Ã%') AS rows_affected, COUNT(*) AS total FROM staging.neighbourhoods
UNION ALL SELECT 'neighbourhoods.neighbourhood', COUNT(*) FILTER (WHERE neighbourhood LIKE '%Ã%'), COUNT(*) FROM staging.neighbourhoods
UNION ALL SELECT 'listings.neighbourhood_group_cleansed', COUNT(*) FILTER (WHERE neighbourhood_group_cleansed LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'listings.neighbourhood_cleansed', COUNT(*) FILTER (WHERE neighbourhood_cleansed LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'listings.name', COUNT(*) FILTER (WHERE name LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'reviews.comments', COUNT(*) FILTER (WHERE comments LIKE '%Ã%'), COUNT(*) FROM staging.reviews;

-- @query Province values as they appear in the files
SELECT neighbourhood_group AS raw_province, COUNT(*) AS municipalities
FROM staging.neighbourhoods GROUP BY 1 ORDER BY 1;

-- @query Raw referential integrity (orphans)
SELECT 'calendar.listing_id without listing' AS check_name,
       COUNT(*) AS row_count FROM staging.calendar c
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.id = c.listing_id)
UNION ALL
SELECT 'reviews.listing_id without listing', COUNT(*) FROM staging.reviews r
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.id = r.listing_id)
UNION ALL
SELECT 'listings whose municipality is not in neighbourhoods.csv', COUNT(*) FROM staging.listings l
       WHERE NOT EXISTS (SELECT 1 FROM staging.neighbourhoods n WHERE n.neighbourhood = l.neighbourhood_cleansed)
UNION ALL
SELECT 'listings without any calendar row', COUNT(*) FROM staging.listings l
       WHERE NOT EXISTS (SELECT 1 FROM staging.calendar c WHERE c.listing_id = l.id)
UNION ALL
SELECT 'municipalities in neighbourhoods.csv without listings', COUNT(*) FROM staging.neighbourhoods n
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.neighbourhood_cleansed = n.neighbourhood);

-- @query Logical inconsistencies
SELECT 'first_review > last_review' AS check_name, COUNT(*) AS row_count
       FROM staging.listings WHERE first_review::date > last_review::date
UNION ALL SELECT 'listings.minimum_nights > maximum_nights', COUNT(*)
       FROM staging.listings WHERE minimum_nights::bigint > maximum_nights::bigint
UNION ALL SELECT 'calendar.minimum_nights > maximum_nights', COUNT(*)
       FROM staging.calendar WHERE minimum_nights::bigint > maximum_nights::bigint
UNION ALL SELECT 'number_of_reviews = 0 but first_review present', COUNT(*)
       FROM staging.listings WHERE number_of_reviews::int = 0 AND first_review IS NOT NULL
UNION ALL SELECT 'maximum_nights > 1125 (usual Airbnb cap)', COUNT(*)
       FROM staging.listings WHERE maximum_nights::bigint > 1125
UNION ALL SELECT 'reviews dated after the scrape', COUNT(*)
       FROM staging.reviews WHERE date::date > (SELECT MAX(last_scraped::date) FROM staging.listings)
UNION ALL SELECT 'host_since after first_review', COUNT(*)
       FROM staging.listings WHERE host_since::date > first_review::date;

-- @query Reviews in the file against number_of_reviews declared by the listing
SELECT COUNT(*) AS listings,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int = COALESCE(r.n, 0)) AS matching,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int > COALESCE(r.n, 0)) AS declared_higher,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int < COALESCE(r.n, 0)) AS declared_lower
FROM staging.listings l
LEFT JOIN (SELECT listing_id, COUNT(*) AS n FROM staging.reviews GROUP BY listing_id) r ON r.listing_id = l.id;

-- @query Listing columns that are 100% empty (discarded)
SELECT kv.key AS column_name
FROM staging.listings t CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) kv
GROUP BY kv.key
HAVING COUNT(*) FILTER (WHERE kv.value IS NOT NULL AND btrim(kv.value) <> '') = 0
ORDER BY 1;

-- @query Values of room_type and number of property types
SELECT 'room_type = ' || room_type AS value, COUNT(*) AS listings FROM staging.listings GROUP BY room_type
UNION ALL SELECT 'distinct property_type values', COUNT(DISTINCT property_type) FROM staging.listings
ORDER BY listings DESC;

-- @query Format of amenities (text holding a JSON list) and number of distinct amenities
SELECT COUNT(*) FILTER (WHERE amenities ~ '^\[.*\]$') AS rows_json_list_format,
       COUNT(*) FILTER (WHERE amenities = '[]')        AS empty_lists,
       (SELECT COUNT(DISTINCT a) FROM staging.listings, jsonb_array_elements_text(amenities::jsonb) a) AS distinct_amenities,
       (SELECT COUNT(*) FROM staging.listings, jsonb_array_elements_text(amenities::jsonb) a) AS listing_amenity_pairs
FROM staging.listings;

-- @query Codes with an unclear meaning: values of 'source' and 'host_verifications'
SELECT 'source = ' || COALESCE(source, '(NULL)') AS value, COUNT(*) AS row_count FROM staging.listings GROUP BY source
UNION ALL
SELECT 'host_verifications = ' || COALESCE(host_verifications, '(NULL)'), COUNT(*) FROM staging.listings GROUP BY host_verifications
ORDER BY row_count DESC;

-- @query Format of license (free text with HTML <br />)
SELECT CASE WHEN license IS NULL OR license = '' THEN '(empty)'
            WHEN license ILIKE '%exempt%' THEN 'exempt'
            WHEN license LIKE '%<br%' THEN 'contains HTML <br />'
            ELSE 'other' END AS kind,
       COUNT(*) AS row_count
FROM staging.listings GROUP BY 1 ORDER BY row_count DESC;

-- @query Fully duplicated rows in calendar and reviews
SELECT 'calendar' AS file, COUNT(*) - COUNT(DISTINCT c.*) AS duplicated_rows FROM staging.calendar c
UNION ALL
SELECT 'reviews', COUNT(*) - COUNT(DISTINCT r.*) FROM staging.reviews r;
