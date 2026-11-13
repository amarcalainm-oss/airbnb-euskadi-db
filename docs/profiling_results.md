# Resultados del perfilado de los datos en bruto

_Generado automáticamente por `scripts/run_profiling.py` el 2026-11-13 13:05._
_Cada tabla es el resultado literal de una consulta SQL sobre el esquema `staging`._

## 01_row_counts

Fichero: `sql/profiling/01_row_counts.sql`

### Filas por fichero

| fichero | filas |
|---|---|
| calendar.csv | 2280744 |
| reviews.csv | 432956 |
| listings.csv | 6248 |
| neighbourhoods.csv | 255 |

### Columnas por fichero

| fichero | columnas |
|---|---|
| listings | 90 |
| reviews | 6 |
| calendar | 5 |
| neighbourhoods | 2 |

## 02_nulls

Fichero: `sql/profiling/02_nulls.sql`

### Nulos por columna - listings (solo columnas con algún nulo)

| columna | nulos | pct_nulos |
|---|---|---|
| bathrooms | 6248 | 100.0 |
| calendar_updated | 6248 | 100.0 |
| host_acceptance_rate | 6248 | 100.0 |
| host_neighbourhood | 6248 | 100.0 |
| host_response_rate | 6248 | 100.0 |
| host_response_time | 6248 | 100.0 |
| host_since | 6248 | 100.0 |
| host_thumbnail_url | 6248 | 100.0 |
| host_total_listings_count | 6248 | 100.0 |
| instant_bookable | 6248 | 100.0 |
| neighborhood_overview | 6248 | 100.0 |
| neighbourhood | 6248 | 100.0 |
| source | 5395 | 86.3 |
| host_about | 3270 | 52.3 |
| host_location | 1833 | 29.3 |
| license | 1120 | 17.9 |
| price_quote_price_per_night | 766 | 12.3 |
| price_quote_total_price | 766 | 12.3 |
| estimated_revenue_l365d | 708 | 11.3 |
| price | 708 | 11.3 |
| price_quote_checkin_date | 520 | 8.3 |
| price_quote_checkout_date | 520 | 8.3 |
| price_quote_raw | 520 | 8.3 |
| first_review | 513 | 8.2 |
| last_review | 513 | 8.2 |
| review_scores_accuracy | 513 | 8.2 |
| review_scores_checkin | 513 | 8.2 |
| review_scores_cleanliness | 513 | 8.2 |
| review_scores_communication | 513 | 8.2 |
| review_scores_location | 513 | 8.2 |
| review_scores_rating | 513 | 8.2 |
| review_scores_value | 513 | 8.2 |
| reviews_per_month | 513 | 8.2 |
| maximum_maximum_nights | 405 | 6.5 |
| maximum_minimum_nights | 405 | 6.5 |
| maximum_nights | 405 | 6.5 |
| minimum_maximum_nights | 405 | 6.5 |
| minimum_minimum_nights | 405 | 6.5 |
| minimum_nights | 405 | 6.5 |
| beds | 108 | 1.7 |
| has_availability | 23 | 0.4 |
| bathrooms_text | 17 | 0.3 |
| description | 12 | 0.2 |
| bedrooms | 3 | 0.0 |

### Nulos por columna - calendar

| columna | nulos |
|---|---|
| available | 0 |
| date | 0 |
| listing_id | 0 |
| maximum_nights | 0 |
| minimum_nights | 0 |

### Nulos por columna - reviews

| columna | nulos |
|---|---|
| comments | 0 |
| date | 0 |
| id | 0 |
| listing_id | 0 |
| reviewer_id | 0 |
| reviewer_name | 0 |

### Nulos por columna - neighbourhoods

| columna | nulos |
|---|---|
| neighbourhood | 0 |
| neighbourhood_group | 0 |

## 03_candidate_keys

Fichero: `sql/profiling/03_candidate_keys.sql`

### Unicidad de claves candidatas

| clave_candidata | total | distintos | nulos |
|---|---|---|---|
| neighbourhoods.neighbourhood | 255 | 255 | 0 |
| listings.id | 6248 | 6248 | 0 |
| hosts: listings.host_id (distintos) | 6248 | 3094 | 0 |
| reviews.id | 432956 | 419594 | 0 |
| reviews.(listing_id, id) | 432956 | 432956 | 0 |
| calendar.(listing_id, date) | 2280744 | 2280744 | 0 |

### reviews.id repetidos: ¿en qué columnas difieren las copias?

| ids_repetidos | filas_implicadas | con_fecha_distinta | con_reviewer_distinto | con_comentario_distinto | con_anuncio_distinto |
|---|---|---|---|---|---|
| 8074 | 21436 | 0 | 0 | 0 | 8074 |

### Ejemplo de reseña repetida (mismo id en varios anuncios del mismo anfitrión)

| review_id | listing_id | host_id | date | reviewer_id |
|---|---|---|---|---|
| 1000528943106590587 | 858805652001140288 | 80463557 | 2023-10-12 | 28462551 |
| 1000528943106590587 | 858829788308660266 | 80463557 | 2023-10-12 | 28462551 |

### ¿Las copias repetidas pertenecen siempre al mismo anfitrión?

| ids_repetidos | mismo_anfitrion | distinto_anfitrion |
|---|---|---|
| 8074 | 8074 | 0 |

### Dependencia funcional host_id -> atributos del anfitrión

| hosts | hosts_con_datos_inconsistentes |
|---|---|
| 3094 | 0 |

### Dependencia funcional reviewer_id -> reviewer_name

| reviewer_id | nombres_distintos | nombres |
|---|---|---|
| 27989262 | 2 | John \| John Mark |
| 498532061 | 2 | Max \| PPM - Lettings And Management |

### Dependencia funcional municipio -> provincia (neighbourhoods.csv)

| municipios | municipios_en_varias_provincias |
|---|---|
| 255 | 0 |

## 04_ranges_formats

Fichero: `sql/profiling/04_ranges_formats.sql`

### Formato y rango de las fechas

| columna | mal_formato | minimo | maximo |
|---|---|---|---|
| listings.last_scraped | 0 | 2026-09-28 | 2026-09-29 |
| listings.host_since | 0 | NULL | NULL |
| listings.first_review | 0 | 2011-06-04 | 2026-09-25 |
| listings.last_review | 0 | 2016-07-08 | 2026-09-28 |
| calendar.date | 0 | 2026-09-28 | 2027-09-28 |
| reviews.date | 0 | 2011-06-04 | 2026-09-28 |

### Formato del precio (texto con símbolo $ y comas de miles)

| formato | filas | ejemplo |
|---|---|---|
| $#,###.## (correcto) | 5540 | $1,000.00 |
| (vacío) | 708 | NULL |

### Rangos numéricos de listings

| columna | minimo | mediana | maximo |
|---|---|---|---|
| price ($) | 14.77 | 160.275 | 10850.00 |
| latitude | 42.48764 | 43.301334999999995 | 43.44149 |
| longitude | -3.4411444142460823 | -2.67346095 | -1.75701 |
| accommodates | 1 | 4.0 | 16 |
| bedrooms | 0 | 2.0 | 25 |
| beds | 1 | 3.0 | 29 |
| bathrooms | NULL | NULL | NULL |
| minimum_nights | 1 | 2.0 | 100 |
| maximum_nights | 1 | 365.0 | 1500 |
| availability_365 | 0 | 169.0 | 365 |
| number_of_reviews | 0 | 32.0 | 1361 |
| review_scores_rating | 1.0 | 4.82 | 5.0 |
| estimated_revenue_l365d | 0 | 9543.0 | 371700 |
| host_listings_count | 1 | 3.0 | 3110 |

### Rangos numéricos de calendar

| columna | minimo | maximo |
|---|---|---|
| minimum_nights | 1 | 300 |
| maximum_nights | 1 | 1500 |

### Formato de los porcentajes del anfitrión

| columna | formato_nn_pct | valor_na | vacios |
|---|---|---|---|
| host_response_rate | 0 | 0 | 6248 |
| host_acceptance_rate | 0 | 0 | 6248 |

### Valores de las columnas booleanas (se esperan 't' / 'f')

| columna | valor | filas |
|---|---|---|
| calendar.available | f | 1075464 |
| calendar.available | t | 1205280 |
| listings.has_availability | f | 477 |
| listings.has_availability | t | 5748 |
| listings.has_availability | NULL | 23 |
| listings.host_has_profile_pic | f | 256 |
| listings.host_has_profile_pic | t | 5992 |
| listings.host_identity_verified | f | 67 |
| listings.host_identity_verified | t | 6181 |
| listings.host_is_superhost | f | 3839 |
| listings.host_is_superhost | t | 2409 |
| listings.instant_bookable | NULL | 6248 |

## 05_anomalies

Fichero: `sql/profiling/05_anomalies.sql`

### Texto mal codificado (mojibake: 'ú' guardado como 'Ãº', 'Á' como 'Ã' + carácter de control)

| columna | filas_afectadas | total |
|---|---|---|
| neighbourhoods.neighbourhood_group | 145 | 255 |
| neighbourhoods.neighbourhood | 27 | 255 |
| listings.name | 0 | 6248 |
| listings.neighbourhood_cleansed | 1706 | 6248 |
| listings.neighbourhood_group_cleansed | 2978 | 6248 |
| reviews.comments | 4 | 432956 |

### Valores de provincia tal como vienen en los ficheros

| provincia_en_bruto | municipios |
|---|---|
| Ãlava | 55 |
| GuipÃºzcoa | 90 |
| Vizcaya | 110 |

### Integridad referencial en bruto (huérfanos)

| comprobacion | filas |
|---|---|
| listings con municipio que no está en neighbourhoods.csv | 0 |
| municipios de neighbourhoods.csv sin anuncios | 48 |
| reviews.listing_id sin anuncio | 0 |
| calendar.listing_id sin anuncio | 0 |
| anuncios sin ninguna fila en calendar | 0 |

### Incoherencias lógicas

| comprobacion | filas |
|---|---|
| number_of_reviews = 0 pero con first_review | 0 |
| maximum_nights > 1125 (tope habitual de Airbnb) | 1 |
| first_review > last_review | 0 |
| host_since posterior a first_review | 0 |
| listings.minimum_nights > maximum_nights | 2 |
| calendar.minimum_nights > maximum_nights | 763 |
| reseñas con fecha posterior al scrape | 0 |

### Reseñas en el fichero frente a number_of_reviews declarado en el anuncio

| anuncios | coinciden | declarado_mayor | declarado_menor |
|---|---|---|---|
| 6248 | 6248 | 0 | 0 |

### Columnas 100% vacías en listings (no aportan nada; se descartan)

| columna |
|---|
| bathrooms |
| calendar_updated |
| host_acceptance_rate |
| host_neighbourhood |
| host_response_rate |
| host_response_time |
| host_since |
| host_thumbnail_url |
| host_total_listings_count |
| instant_bookable |
| neighborhood_overview |
| neighbourhood |

### Valores de room_type y número de property_type

| valor | anuncios |
|---|---|
| room_type = Entire home/apt | 4534 |
| room_type = Private room | 1618 |
| property_type distintos | 64 |
| room_type = Hotel room | 51 |
| room_type = Shared room | 45 |

### Formato de amenities (texto con una lista JSON) y número de servicios distintos

| filas_formato_lista_json | listas_vacias | servicios_distintos | pares_anuncio_servicio |
|---|---|---|---|
| 6248 | 2 | 1739 | 196014 |

### Códigos con significado poco claro: valores de 'source' y 'host_verifications'

| valor | filas |
|---|---|
| host_verifications = None | 6248 |
| source = (NULL) | 5395 |
| source = previous scrape | 853 |

### Formato de license (texto libre con HTML <br />)

| tipo | filas |
|---|---|
| contiene HTML <br /> | 3992 |
| (vacío) | 1120 |
| exento | 1040 |
| otro | 96 |

### Filas totalmente duplicadas en calendar y reviews

| fichero | filas_duplicadas |
|---|---|
| reviews | 0 |
| calendar | 0 |
