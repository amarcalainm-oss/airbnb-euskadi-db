-- Perfilado 3: claves candidatas. ¿Son realmente únicas?
-- Una columna (o combinación) es clave si total = distintos y no tiene nulos.

-- @query Unicidad de claves candidatas
SELECT 'listings.id' AS clave_candidata, COUNT(*) AS total, COUNT(DISTINCT id) AS distintos,
       COUNT(*) - COUNT(id) AS nulos FROM staging.listings
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
SELECT 'hosts: listings.host_id (distintos)', COUNT(*), COUNT(DISTINCT host_id),
       COUNT(*) - COUNT(host_id) FROM staging.listings;

-- @query reviews.id repetidos: ¿en qué columnas difieren las copias?
-- Si la misma reseña (id) aparece varias veces, miramos si cambia algo más que el anuncio.
SELECT COUNT(*)                                        AS ids_repetidos,
       SUM(n_filas)                                    AS filas_implicadas,
       COUNT(*) FILTER (WHERE n_fechas > 1)            AS con_fecha_distinta,
       COUNT(*) FILTER (WHERE n_reviewers > 1)         AS con_reviewer_distinto,
       COUNT(*) FILTER (WHERE n_comentarios > 1)       AS con_comentario_distinto,
       COUNT(*) FILTER (WHERE n_listings > 1)          AS con_anuncio_distinto
FROM (
    SELECT id, COUNT(*) AS n_filas,
           COUNT(DISTINCT date) AS n_fechas, COUNT(DISTINCT reviewer_id) AS n_reviewers,
           COUNT(DISTINCT md5(comments)) AS n_comentarios, COUNT(DISTINCT listing_id) AS n_listings
    FROM staging.reviews
    GROUP BY id
    HAVING COUNT(*) > 1
) d;

-- @query Ejemplo de reseña repetida (mismo id en varios anuncios del mismo anfitrión)
SELECT r.id AS review_id, r.listing_id, l.host_id, r.date, r.reviewer_id
FROM staging.reviews r
JOIN staging.listings l ON l.id = r.listing_id
WHERE r.id = (SELECT id FROM staging.reviews GROUP BY id HAVING COUNT(*) > 1 ORDER BY id LIMIT 1)
ORDER BY r.listing_id;

-- @query ¿Las copias repetidas pertenecen siempre al mismo anfitrión?
SELECT COUNT(*) AS ids_repetidos,
       COUNT(*) FILTER (WHERE n_hosts = 1) AS mismo_anfitrion,
       COUNT(*) FILTER (WHERE n_hosts > 1) AS distinto_anfitrion
FROM (
    SELECT r.id, COUNT(DISTINCT l.host_id) AS n_hosts
    FROM staging.reviews r JOIN staging.listings l ON l.id = r.listing_id
    GROUP BY r.id HAVING COUNT(*) > 1
) x;

-- @query Dependencia funcional host_id -> atributos del anfitrión
-- Si cada host_id tiene siempre los mismos datos, se pueden sacar a una tabla HOST sin perder nada.
SELECT COUNT(*) AS hosts,
       COUNT(*) FILTER (WHERE n_variantes > 1) AS hosts_con_datos_inconsistentes
FROM (
    SELECT host_id,
           COUNT(DISTINCT (host_name, host_since, host_is_superhost, host_location,
                           host_listings_count, host_total_listings_count,
                           host_identity_verified, host_has_profile_pic)) AS n_variantes
    FROM staging.listings GROUP BY host_id
) h;

-- @query Dependencia funcional reviewer_id -> reviewer_name
SELECT reviewer_id, COUNT(DISTINCT reviewer_name) AS nombres_distintos,
       string_agg(DISTINCT reviewer_name, ' | ') AS nombres
FROM staging.reviews
GROUP BY reviewer_id
HAVING COUNT(DISTINCT reviewer_name) > 1;

-- @query Dependencia funcional municipio -> provincia (neighbourhoods.csv)
SELECT COUNT(*) AS municipios,
       COUNT(*) FILTER (WHERE n_prov > 1) AS municipios_en_varias_provincias
FROM (SELECT neighbourhood, COUNT(DISTINCT neighbourhood_group) AS n_prov
      FROM staging.neighbourhoods GROUP BY neighbourhood) x;
