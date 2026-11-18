SELECT rel.relname                       AS table_name,
       con.conname                       AS constraint_name,
       CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                        WHEN 'u' THEN 'UNIQUE'      WHEN 'c' THEN 'CHECK'
                        WHEN 'n' THEN 'NOT NULL' END AS constraint_type,
       pg_get_constraintdef(con.oid)     AS definition,
       con.convalidated                  AS validated
FROM pg_constraint con
JOIN pg_class      rel ON rel.oid = con.conrelid
JOIN pg_namespace  nsp ON nsp.oid = rel.relnamespace
WHERE nsp.nspname = 'airbnb'
ORDER BY table_name, constraint_type, constraint_name;

SELECT CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                        WHEN 'u' THEN 'UNIQUE'      WHEN 'c' THEN 'CHECK'
                        WHEN 'n' THEN 'NOT NULL' END AS constraint_type,
       COUNT(*) AS total
FROM pg_constraint con
JOIN pg_namespace nsp ON nsp.oid = con.connamespace
WHERE nsp.nspname = 'airbnb'
GROUP BY 1 ORDER BY 2 DESC;

-- Each statement must be rejected
-- BEGIN;
-- INSERT INTO airbnb.listing_review VALUES (-1, -1);  -- FK
-- UPDATE airbnb.listing SET price = -5 WHERE listing_id = 132068;  -- CHECK
-- UPDATE airbnb.listing SET room_type = 'Castle' WHERE listing_id = 132068;  -- CHECK
-- INSERT INTO airbnb.province (name) VALUES ('Vizcaya');  -- UNIQUE
-- UPDATE airbnb.calendar_day SET available = NULL WHERE listing_id = 132068;  -- NOT NULL
-- ROLLBACK;

SELECT 'province' AS table_name, COUNT(*) AS row_count FROM airbnb.province
UNION ALL SELECT 'municipality',    COUNT(*) FROM airbnb.municipality
UNION ALL SELECT 'host',            COUNT(*) FROM airbnb.host
UNION ALL SELECT 'property_type',   COUNT(*) FROM airbnb.property_type
UNION ALL SELECT 'listing',         COUNT(*) FROM airbnb.listing
UNION ALL SELECT 'amenity',         COUNT(*) FROM airbnb.amenity
UNION ALL SELECT 'listing_amenity', COUNT(*) FROM airbnb.listing_amenity
UNION ALL SELECT 'calendar_day',    COUNT(*) FROM airbnb.calendar_day
UNION ALL SELECT 'reviewer',        COUNT(*) FROM airbnb.reviewer
UNION ALL SELECT 'review',          COUNT(*) FROM airbnb.review
UNION ALL SELECT 'listing_review',  COUNT(*) FROM airbnb.listing_review;
