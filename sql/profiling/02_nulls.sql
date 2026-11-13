-- Perfilado 2: nulos por columna.
-- Truco: to_jsonb(fila) convierte cada fila en un objeto {columna: valor} y
-- jsonb_each_text lo "despliega" en pares (columna, valor). Así contamos los
-- nulos de TODAS las columnas con una sola consulta, sin escribirlas a mano.
-- Contamos como vacío tanto NULL como la cadena '' (en CSV ambas significan "falta el dato").

-- @query Nulos por columna - listings (solo columnas con algún nulo)
SELECT kv.key AS columna,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulos,
       ROUND(100.0 * COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') / COUNT(*), 1) AS pct_nulos
FROM staging.listings t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
HAVING COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') > 0
ORDER BY nulos DESC, columna;

-- @query Nulos por columna - calendar
SELECT kv.key AS columna,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulos
FROM staging.calendar t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY columna;

-- @query Nulos por columna - reviews
SELECT kv.key AS columna,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulos
FROM staging.reviews t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY columna;

-- @query Nulos por columna - neighbourhoods
SELECT kv.key AS columna,
       COUNT(*) FILTER (WHERE kv.value IS NULL OR btrim(kv.value) = '') AS nulos
FROM staging.neighbourhoods t
CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) AS kv
GROUP BY kv.key
ORDER BY columna;
