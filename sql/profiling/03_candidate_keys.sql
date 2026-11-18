-- @query Uniqueness of candidate keys
SELECT 'listings.id' AS candidate_key, COUNT(*) AS total, COUNT(DISTINCT id) AS distinct_values,
       COUNT(*) - COUNT(id) AS nulls FROM staging.listings
UNION ALL
SELECT 'neighbourhoods.neighbourhood', COUNT(*), COUNT(DISTINCT neighbourhood),
       COUNT(*) - COUNT(neighbourhood) FROM staging.neighbourhoods
UNION ALL
SELECT 'calendar.(listing_id, date)', COUNT(*), COUNT(DISTINCT (listing_id, date)),
       COUNT(*) FILTER (WHERE listing_id IS NULL OR date IS NULL) FROM staging.calendar
UNION ALL
SELECT 'reviews.id', COUNT(*), COUNT(DISTINCT id), COUNT(*) - COUNT(id) FROM staging.reviews
UNION ALL
SELECT 'reviews.(listing_id, id)', COUNT(*), COUNT(DISTINCT (listing_id, id)),
       COUNT(*) FILTER (WHERE listing_id IS NULL OR id IS NULL) FROM staging.reviews
UNION ALL
SELECT 'hosts: listings.host_id (distinct)', COUNT(*), COUNT(DISTINCT host_id),
       COUNT(*) - COUNT(host_id) FROM staging.listings;

-- @query Repeated reviews.id: in which columns do the copies differ?
SELECT COUNT(*)                                        AS repeated_ids,
       SUM(n_rows)                                     AS rows_involved,
       COUNT(*) FILTER (WHERE n_dates > 1)             AS with_different_date,
       COUNT(*) FILTER (WHERE n_reviewers > 1)         AS with_different_reviewer,
       COUNT(*) FILTER (WHERE n_comments > 1)          AS with_different_comment,
       COUNT(*) FILTER (WHERE n_listings > 1)          AS with_different_listing
FROM (
    SELECT id, COUNT(*) AS n_rows,
           COUNT(DISTINCT date) AS n_dates, COUNT(DISTINCT reviewer_id) AS n_reviewers,
           COUNT(DISTINCT md5(comments)) AS n_comments, COUNT(DISTINCT listing_id) AS n_listings
    FROM staging.reviews
    GROUP BY id
    HAVING COUNT(*) > 1
) d;

-- @query Example of a repeated review (same id on several listings of the same host)
SELECT r.id AS review_id, r.listing_id, l.host_id, r.date, r.reviewer_id
FROM staging.reviews r
JOIN staging.listings l ON l.id = r.listing_id
WHERE r.id = (SELECT id FROM staging.reviews GROUP BY id HAVING COUNT(*) > 1 ORDER BY id LIMIT 1)
ORDER BY r.listing_id;

-- @query Do the repeated copies always belong to the same host?
SELECT COUNT(*) AS repeated_ids,
       COUNT(*) FILTER (WHERE n_hosts = 1) AS same_host,
       COUNT(*) FILTER (WHERE n_hosts > 1) AS different_host
FROM (
    SELECT r.id, COUNT(DISTINCT l.host_id) AS n_hosts
    FROM staging.reviews r JOIN staging.listings l ON l.id = r.listing_id
    GROUP BY r.id HAVING COUNT(*) > 1
) x;

-- @query Functional dependency host_id -> host attributes
SELECT COUNT(*) AS hosts,
       COUNT(*) FILTER (WHERE n_variants > 1) AS hosts_with_inconsistent_data
FROM (
    SELECT host_id,
           COUNT(DISTINCT (host_name, host_since, host_is_superhost, host_location,
                           host_listings_count, host_total_listings_count,
                           host_identity_verified, host_has_profile_pic)) AS n_variants
    FROM staging.listings GROUP BY host_id
) h;

-- @query Functional dependency reviewer_id -> reviewer_name
SELECT reviewer_id, COUNT(DISTINCT reviewer_name) AS distinct_names,
       string_agg(DISTINCT reviewer_name, ' | ') AS names
FROM staging.reviews
GROUP BY reviewer_id
HAVING COUNT(DISTINCT reviewer_name) > 1;

-- @query Functional dependency municipality -> province (neighbourhoods.csv)
SELECT COUNT(*) AS municipalities,
       COUNT(*) FILTER (WHERE n_prov > 1) AS municipalities_in_several_provinces
FROM (SELECT neighbourhood, COUNT(DISTINCT neighbourhood_group) AS n_prov
      FROM staging.neighbourhoods GROUP BY neighbourhood) x;

-- @query Repeated review ids: are they identical copies?
SELECT COUNT(*) AS repeated_ids,
       SUM(n_rows - 1) AS surplus_rows,
       COUNT(*) FILTER (WHERE n_texts > 1) AS with_different_text,
       COUNT(*) FILTER (WHERE n_dates > 1) AS with_different_date,
       COUNT(*) FILTER (WHERE n_authors > 1) AS with_different_author,
       COUNT(*) FILTER (WHERE n_listings < n_rows) AS repeated_on_same_listing
FROM (SELECT id, COUNT(*) AS n_rows, COUNT(DISTINCT comments) AS n_texts,
             COUNT(DISTINCT date) AS n_dates, COUNT(DISTINCT reviewer_id) AS n_authors,
             COUNT(DISTINCT listing_id) AS n_listings
      FROM staging.reviews GROUP BY id HAVING COUNT(*) > 1) x;
