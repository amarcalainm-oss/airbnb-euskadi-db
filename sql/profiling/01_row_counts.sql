-- Perfilado 1: número de filas de cada fichero en bruto.
-- (Cada bloque que empieza por "-- @query" es una consulta independiente;
--  scripts/run_profiling.py las ejecuta y vuelca el resultado a docs/profiling_results.md)

-- @query Filas por fichero
SELECT 'neighbourhoods.csv' AS fichero, COUNT(*) AS filas FROM staging.neighbourhoods
UNION ALL SELECT 'listings.csv', COUNT(*) FROM staging.listings
UNION ALL SELECT 'calendar.csv', COUNT(*) FROM staging.calendar
UNION ALL SELECT 'reviews.csv',  COUNT(*) FROM staging.reviews
ORDER BY filas DESC;

-- @query Columnas por fichero
SELECT table_name AS fichero, COUNT(*) AS columnas
FROM information_schema.columns
WHERE table_schema = 'staging'
GROUP BY table_name
ORDER BY columnas DESC;
