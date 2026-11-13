# Informe de limpieza (ETL)

_Generado automáticamente por `scripts/etl.py`._

## Reglas de limpieza y filas afectadas

| Regla | Descripción | Filas afectadas |
|---|---|---|
| R01 | Texto con doble codificación UTF-8 (mojibake, p. ej. 'GuipÃºzcoa' -> 'Guipúzcoa') reparado (nº de celdas) | 4,856 |
| R02 | Cadena vacía convertida en NULL (anuncios con al menos una celda vacía en columnas cargadas) | 6,193 |
| R03 | Precio en texto '$1,234.00' convertido a NUMERIC 1234.00 | 5,540 |
| R04 | Booleanos 't'/'f' convertidos a TRUE/FALSE (anuncios) | 6,248 |
| R05 | bathrooms_text separado en bathrooms (número) y bathroom_shared (booleano) | 6,231 |
| R06 | Coordenadas con más de 6 decimales redondeadas a 6 (≈0,1 m) | 4,858 |
| R07 | Etiquetas HTML <br /> sustituidas por ' \| ' en license | 5,029 |
| R08 | Etiquetas HTML <br> sustituidas por salto de línea en description | 3,539 |
| R09 | Etiquetas HTML <br> sustituidas por salto de línea en reviews.comments | 100,809 |
| R10 | Antigüedad del anfitrión 'años + meses' convertida a meses totales | 3,094 |
| R11 | listing con minimum_nights > maximum_nights: ambos se dejan a NULL (no se sabe cuál es erróneo) | 2 |
| R12 | calendar con minimum_nights > maximum_nights: ambos se dejan a NULL | 763 |
| R13 | amenities: lista JSON separada en filas de listing_amenity | 6,246 |
| R14 | amenities: servicios repetidos dentro del mismo anuncio eliminados | 0 |
| R15 | reviewer con varios nombres: se toma el de su reseña más reciente | 2 |
| R16 | review id repetido en varios anuncios: se guarda una sola reseña (filas fusionadas) | 13,362 |

## Filas cargadas por tabla

| Tabla | Filas |
|---|---|
| province | 3 |
| municipality | 255 |
| host | 3,094 |
| property_type | 64 |
| listing | 6,248 |
| amenity | 1,739 |
| listing_amenity | 196,014 |
| calendar_day | 2,280,744 |
| reviewer | 381,425 |
| review | 419,594 |
| listing_review | 432,956 |
