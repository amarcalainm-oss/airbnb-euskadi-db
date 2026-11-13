-- Perfilado 5: duplicados, códigos sin significado claro y cosas inesperadas.

-- @query Texto mal codificado (mojibake: 'ú' guardado como 'Ãº', 'Á' como 'Ã' + carácter de control)
SELECT 'neighbourhoods.neighbourhood_group' AS columna, COUNT(*) FILTER (WHERE neighbourhood_group LIKE '%Ã%') AS filas_afectadas, COUNT(*) AS total FROM staging.neighbourhoods
UNION ALL SELECT 'neighbourhoods.neighbourhood', COUNT(*) FILTER (WHERE neighbourhood LIKE '%Ã%'), COUNT(*) FROM staging.neighbourhoods
UNION ALL SELECT 'listings.neighbourhood_group_cleansed', COUNT(*) FILTER (WHERE neighbourhood_group_cleansed LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'listings.neighbourhood_cleansed', COUNT(*) FILTER (WHERE neighbourhood_cleansed LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'listings.name', COUNT(*) FILTER (WHERE name LIKE '%Ã%'), COUNT(*) FROM staging.listings
UNION ALL SELECT 'reviews.comments', COUNT(*) FILTER (WHERE comments LIKE '%Ã%'), COUNT(*) FROM staging.reviews;

-- @query Valores de provincia tal como vienen en los ficheros
SELECT neighbourhood_group AS provincia_en_bruto, COUNT(*) AS municipios
FROM staging.neighbourhoods GROUP BY 1 ORDER BY 1;

-- @query Integridad referencial en bruto (huérfanos)
SELECT 'calendar.listing_id sin anuncio' AS comprobacion,
       COUNT(*) AS filas FROM staging.calendar c
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.id = c.listing_id)
UNION ALL
SELECT 'reviews.listing_id sin anuncio', COUNT(*) FROM staging.reviews r
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.id = r.listing_id)
UNION ALL
SELECT 'listings con municipio que no está en neighbourhoods.csv', COUNT(*) FROM staging.listings l
       WHERE NOT EXISTS (SELECT 1 FROM staging.neighbourhoods n WHERE n.neighbourhood = l.neighbourhood_cleansed)
UNION ALL
SELECT 'anuncios sin ninguna fila en calendar', COUNT(*) FROM staging.listings l
       WHERE NOT EXISTS (SELECT 1 FROM staging.calendar c WHERE c.listing_id = l.id)
UNION ALL
SELECT 'municipios de neighbourhoods.csv sin anuncios', COUNT(*) FROM staging.neighbourhoods n
       WHERE NOT EXISTS (SELECT 1 FROM staging.listings l WHERE l.neighbourhood_cleansed = n.neighbourhood);

-- @query Incoherencias lógicas
SELECT 'first_review > last_review' AS comprobacion, COUNT(*) AS filas
       FROM staging.listings WHERE first_review::date > last_review::date
UNION ALL SELECT 'listings.minimum_nights > maximum_nights', COUNT(*)
       FROM staging.listings WHERE minimum_nights::bigint > maximum_nights::bigint
UNION ALL SELECT 'calendar.minimum_nights > maximum_nights', COUNT(*)
       FROM staging.calendar WHERE minimum_nights::bigint > maximum_nights::bigint
UNION ALL SELECT 'number_of_reviews = 0 pero con first_review', COUNT(*)
       FROM staging.listings WHERE number_of_reviews::int = 0 AND first_review IS NOT NULL
UNION ALL SELECT 'maximum_nights > 1125 (tope habitual de Airbnb)', COUNT(*)
       FROM staging.listings WHERE maximum_nights::bigint > 1125
UNION ALL SELECT 'reseñas con fecha posterior al scrape', COUNT(*)
       FROM staging.reviews WHERE date::date > (SELECT MAX(last_scraped::date) FROM staging.listings)
UNION ALL SELECT 'host_since posterior a first_review', COUNT(*)
       FROM staging.listings WHERE host_since::date > first_review::date;

-- @query Reseñas en el fichero frente a number_of_reviews declarado en el anuncio
SELECT COUNT(*) AS anuncios,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int = COALESCE(r.n, 0)) AS coinciden,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int > COALESCE(r.n, 0)) AS declarado_mayor,
       COUNT(*) FILTER (WHERE l.number_of_reviews::int < COALESCE(r.n, 0)) AS declarado_menor
FROM staging.listings l
LEFT JOIN (SELECT listing_id, COUNT(*) AS n FROM staging.reviews GROUP BY listing_id) r ON r.listing_id = l.id;

-- @query Columnas 100% vacías en listings (no aportan nada; se descartan)
SELECT kv.key AS columna
FROM staging.listings t CROSS JOIN LATERAL jsonb_each_text(to_jsonb(t)) kv
GROUP BY kv.key
HAVING COUNT(*) FILTER (WHERE kv.value IS NOT NULL AND btrim(kv.value) <> '') = 0
ORDER BY 1;

-- @query Valores de room_type y número de property_type
SELECT 'room_type = ' || room_type AS valor, COUNT(*) AS anuncios FROM staging.listings GROUP BY room_type
UNION ALL SELECT 'property_type distintos', COUNT(DISTINCT property_type) FROM staging.listings
ORDER BY anuncios DESC;

-- @query Formato de amenities (texto con una lista JSON) y número de servicios distintos
SELECT COUNT(*) FILTER (WHERE amenities ~ '^\[.*\]$') AS filas_formato_lista_json,
       COUNT(*) FILTER (WHERE amenities = '[]')        AS listas_vacias,
       (SELECT COUNT(DISTINCT a) FROM staging.listings, jsonb_array_elements_text(amenities::jsonb) a) AS servicios_distintos,
       (SELECT COUNT(*) FROM staging.listings, jsonb_array_elements_text(amenities::jsonb) a) AS pares_anuncio_servicio
FROM staging.listings;

-- @query Códigos con significado poco claro: valores de 'source' y 'host_verifications'
SELECT 'source = ' || COALESCE(source, '(NULL)') AS valor, COUNT(*) AS filas FROM staging.listings GROUP BY source
UNION ALL
SELECT 'host_verifications = ' || COALESCE(host_verifications, '(NULL)'), COUNT(*) FROM staging.listings GROUP BY host_verifications
ORDER BY filas DESC;

-- @query Formato de license (texto libre con HTML <br />)
SELECT CASE WHEN license IS NULL OR license = '' THEN '(vacío)'
            WHEN license ILIKE '%exempt%' THEN 'exento'
            WHEN license LIKE '%<br%' THEN 'contiene HTML <br />'
            ELSE 'otro' END AS tipo,
       COUNT(*) AS filas
FROM staging.listings GROUP BY 1 ORDER BY filas DESC;

-- @query Filas totalmente duplicadas en calendar y reviews
SELECT 'calendar' AS fichero, COUNT(*) - COUNT(DISTINCT c.*) AS filas_duplicadas FROM staging.calendar c
UNION ALL
SELECT 'reviews', COUNT(*) - COUNT(DISTINCT r.*) FROM staging.reviews r;
