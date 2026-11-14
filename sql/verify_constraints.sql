SELECT rel.relname                       AS tabla,
       con.conname                       AS restriccion,
       CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                        WHEN 'u' THEN 'UNIQUE'      WHEN 'c' THEN 'CHECK'
                        WHEN 'n' THEN 'NOT NULL' END AS tipo,
       pg_get_constraintdef(con.oid)     AS definicion,
       con.convalidated                  AS validada
FROM pg_constraint con
JOIN pg_class      rel ON rel.oid = con.conrelid
JOIN pg_namespace  nsp ON nsp.oid = rel.relnamespace
WHERE nsp.nspname = 'airbnb'
ORDER BY tabla, tipo, restriccion;

SELECT CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                        WHEN 'u' THEN 'UNIQUE'      WHEN 'c' THEN 'CHECK'
                        WHEN 'n' THEN 'NOT NULL' END AS tipo,
       COUNT(*) AS cantidad
FROM pg_constraint con
JOIN pg_namespace nsp ON nsp.oid = con.connamespace
WHERE nsp.nspname = 'airbnb'
GROUP BY 1 ORDER BY 2 DESC;

-- Deben fallar
-- BEGIN;
-- INSERT INTO airbnb.listing_review VALUES (-1, -1);  -- FK
-- UPDATE airbnb.listing SET price = -5 WHERE listing_id = 132068;  -- CHECK
-- UPDATE airbnb.listing SET room_type = 'Castle' WHERE listing_id = 132068;  -- CHECK
-- INSERT INTO airbnb.province (name) VALUES ('Vizcaya');  -- UNIQUE
-- UPDATE airbnb.calendar_day SET available = NULL WHERE listing_id = 132068;  -- NOT NULL
-- ROLLBACK;

SELECT 'province' AS tabla, COUNT(*) AS filas FROM airbnb.province
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
