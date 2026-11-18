-- @query Nulls per column - listings (only columns with at least one null)
SELECT kv.key AS column_name,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulls,
       ROUND(100.0 * COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') / COUNT(*), 1) AS pct_nulls
FROM staging.listings t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
HAVING COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') > 0
ORDER BY nulls DESC, column_name;

-- @query Nulls per column - calendar
SELECT kv.key AS column_name,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulls
FROM staging.calendar t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY column_name;

-- @query Nulls per column - reviews
SELECT kv.key AS column_name,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulls
FROM staging.reviews t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY column_name;

-- @query Nulls per column - neighbourhoods
SELECT kv.key AS column_name,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulls
FROM staging.neighbourhoods t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY column_name;
