# Guía paso a paso del proyecto

Esta guía explica **qué se hizo, por qué y cómo comprobarlo**, en el mismo orden en que se
construyó el proyecto. Está pensada para que cualquiera del equipo pueda defender cualquier
parte en la presentación: el enunciado avisa de que se puede preguntar a cualquiera sobre todo.

Cada paso se divide en: objetivo, qué se hizo, cómo ejecutarlo, resultado y qué decir si
preguntan en la presentación.

---

## Paso 0 - Herramientas y preparación

**Objetivo.** Tener el entorno listo.

**Qué se hizo.** Comprobamos lo que ya estaba instalado en el ordenador:

| Herramienta | Versión | Para qué |
|---|---|---|
| PostgreSQL | 18 (servicio `postgresql-x64-18`) | base de datos |
| pgAdmin 4 | incluido con PostgreSQL 18 | ver tablas y restricciones, capturas |
| Python | 3.14 | scripts de carga y app |
| Streamlit, Plotly | 1.63 / 7.1 | visualización |
| psycopg2 | 2.9 (instalado por nosotros) | conexión Python → PostgreSQL |
| git + GitHub CLI (`gh`) | 2.55 / 2.103 | repositorio |

Las credenciales van en un fichero **`.env`** (copia de `.env.example`) que **no** se sube a
GitHub (está en `.gitignore`). `scripts/db.py` las lee y todos los scripts se conectan desde ahí.

**Cómo ejecutarlo.**
```bash
pip install -r requirements.txt
copy .env.example .env      # y escribir la contraseña de postgres en PGPASSWORD=
python scripts/create_database.py
```

**Qué decir si preguntan.** *"La contraseña nunca está en el código; la lee python-dotenv desde un `.env` ignorado por git."*

---

## Paso 1 - Elegir el dataset y descargarlo por script

**Objetivo.** El enunciado pide un dataset real, abierto, relacional, con al menos 3 tablas y una tabla de
más de 10.000 filas. Además, los datos **no se suben a git**: se descargan con un script.

**Qué se hizo.** Dataset: **Inside Airbnb - Euskadi** (scrape del 25-09-2026).
- Fuente identificable: insideairbnb.com · Licencia **CC BY 4.0** (hay que citarla).
- Ficheros: `listings` (anuncios, 79 columnas), `calendar` (disponibilidad diaria),
  `reviews` (reseñas con texto) y `neighbourhoods` (municipio → provincia).
- Comparten claves: `listing_id` une calendar y reviews con listings, y `neighbourhood` une
  listings con neighbourhoods.
- Tabla grande: `calendar` con **2.280.744 filas**.

Usamos el `listings.csv.gz` **detallado** (79 columnas) en vez del resumen de 18 columnas que se
descargó al principio, porque permite un modelo mucho más rico (anfitriones, servicios,
puntuaciones).

**Cómo ejecutarlo.** `python scripts/download_data.py` → guarda todo en `data/raw/` (ignorado por git).

**Resultado.** 4 ficheros, unos 220 MB descomprimidos.

---

## Paso 2 - Meter los CSV "tal cual" en PostgreSQL (esquema `staging`)

**Objetivo.** El enunciado dice que **todo el análisis se hace en SQL**, también el perfilado de los datos en
bruto. Para eso los ficheros tienen que estar dentro de PostgreSQL **antes** de diseñar el modelo.

**Qué se hizo.** `scripts/load_staging.py` crea un esquema auxiliar `staging` con una tabla por fichero, con
**todas las columnas como TEXT**, y copia cada CSV con `COPY ... FROM STDIN`. Todo es TEXT a
propósito: si declarásemos `price NUMERIC`, el valor `"$1,000.00"` haría fallar la carga, y
queremos *ver* esos valores raros, no que nos los oculte un error.

Python aquí solo lee la cabecera del CSV (para saber los nombres de columna) y envía el fichero.
No calcula nada.

**Cómo ejecutarlo.** `python scripts/load_staging.py`

**Resultado.** `staging.calendar` 2.280.744 · `staging.reviews` 432.956 · `staging.listings` 6.248 ·
`staging.neighbourhoods` 255 filas.

**Qué decir si preguntan.** *"`staging` es una zona de aterrizaje; no es nuestro modelo. El modelo es el esquema `airbnb`."*

---

## Paso 3 - Perfilado de los datos (en SQL)

**Objetivo.** Antes de modelar hay que conocer los datos: filas por fichero, claves candidatas, nulos,
rangos y formatos, duplicados y anomalías (apartado *1.a Data analysis* del enunciado).

**Qué se hizo.** Cinco ficheros en `sql/profiling/`, cada uno con varias consultas. `scripts/run_profiling.py`
las ejecuta y escribe los resultados en **[`docs/profiling_results.md`](profiling_results.md)**.

Trucos SQL que conviene entender:
- **Nulos de todas las columnas a la vez:** `to_jsonb(fila)` convierte la fila en
  `{"columna": valor, ...}` y `jsonb_each_text` la despliega en pares (columna, valor). Luego
  basta con un `GROUP BY columna`.
- **¿Es clave?** Si `COUNT(*) = COUNT(DISTINCT col)` y no hay nulos, la columna es candidata a clave.
- **¿Dependencia funcional?** `COUNT(DISTINCT (atributos))` por `host_id` = 1 → los datos del
  anfitrión dependen solo de `host_id` → se pueden sacar a una tabla `host`.
- **Formato antes de convertir:** primero `col ~ '^\d{4}-\d{2}-\d{2}$'` (regex) y después `col::date`.

**Resultado.** **Hallazgos principales** (son los que dan forma al modelo):

| # | Hallazgo | Consecuencia |
|---|---|---|
| 1 | `reviews.id` **no es único**: 8.074 ids aparecen en 2+ anuncios (21.436 filas). Las copias son idénticas salvo el anuncio, y siempre del mismo anfitrión | relación N:M review–listing |
| 2 | Texto con **doble codificación** (`GuipÃºzcoa`, `Ãlava`) en 2.978 anuncios y 145 municipios | regla de limpieza R01 |
| 3 | **12 columnas 100 % vacías** (`host_since`, `host_response_rate`, `bathrooms`, `instant_bookable`…) | no se crean |
| 4 | Precio en texto `"$1,234.00"`, 708 vacíos | conversión a NUMERIC, vacíos → NULL |
| 5 | `minimum_nights > maximum_nights` en 2 anuncios y 763 días de calendario | ambos a NULL |
| 6 | `host_id` → atributos del anfitrión: 0 inconsistencias (3.094 hosts) | tabla HOST |
| 7 | `number_of_reviews` coincide al 100 % con las filas de reviews; `first/last_review` también | no se guardan (derivables) |
| 8 | `amenities` es una lista JSON dentro de una celda: 1.739 servicios distintos, 196.014 pares | tabla N:M |
| 9 | `license` es texto libre con HTML `<br />`; 1.120 vacías, 1.040 "Exempt" | limpieza R07 + consulta Q11 |
| 10 | Integridad referencial en bruto perfecta: 0 huérfanos en calendar y reviews; 48 municipios sin anuncios | FKs viables |
| 11 | 2 reviewers con dos nombres distintos | regla R15 |

**Qué decir si preguntan.** *"El hallazgo más importante fue que el id de reseña no es único. Si no lo hubiéramos perfilado,
la carga con `review_id` como PRIMARY KEY habría fallado."*

---

## Paso 4 - Modelo conceptual, lógico y físico

**Objetivo.** Diagrama ER, modelo relacional y script DDL con todas las restricciones.

**Qué se hizo.** Todo está explicado en **[`docs/modelo.md`](modelo.md)**: el diagrama, el modelo relacional, las
**8 decisiones/excepciones justificadas** y los tipos de datos. El DDL está en
**[`sql/schema.sql`](../sql/schema.sql)**.

11 tablas: `province`, `municipality`, `host`, `property_type`, `listing`, `amenity`,
`listing_amenity`, `calendar_day`, `reviewer`, `review`, `listing_review`.

Restricciones: 11 PRIMARY KEY, 10 FOREIGN KEY, 5 UNIQUE, 29 CHECK y 41 NOT NULL.
Además hay 9 índices sobre las claves foráneas, porque PostgreSQL **no** los crea solo.

**Cómo ejecutarlo.** `python scripts/create_schema.py` (borra y recrea el esquema `airbnb`, vacío).

**Qué decir si preguntan.** *"El esquema lo crea nuestro script antes de cargar; la carga solo hace INSERT/COPY."*

**Pendiente.** Pendiente para el informe: **redibujar el ER en la notación del curso**.

---

## Paso 5 - ETL en una sola transacción

**Objetivo.** Leer los CSV, limpiar formatos e insertar en las tablas ya creadas. **Toda la carga es una
transacción**: o entra todo o no entra nada. Los nulos se quedan como NULL y cada regla de
limpieza se documenta con las filas que toca.

**Qué se hizo.** `scripts/etl.py`:
1. `get_connection()` → psycopg2 abre una transacción automáticamente (autocommit = False).
2. Carga en orden de dependencias (primero los "padres"): province → municipality → host →
   property_type → listing → amenity → listing_amenity → calendar_day → reviewer → review →
   listing_review.
3. Para las tablas grandes usa `COPY ... FROM STDIN` (mucho más rápido que miles de INSERT), que
   sigue dentro de la **misma** transacción.
4. Si todo va bien, `conn.commit()`. Si salta cualquier excepción, `conn.rollback()`.

**Reglas de limpieza** (resultado real en **[`docs/cleaning_report.md`](cleaning_report.md)**):

| Regla | Qué hace | Filas |
|---|---|---|
| R01 | Repara la doble codificación: `s.encode('latin-1').decode('utf-8')` (si falla, el texto ya estaba bien) | 4.856 celdas |
| R02 | Celda vacía → NULL (nunca se rellena) | 6.193 anuncios |
| R03 | `"$1,234.00"` → `1234.00` | 5.540 |
| R04 | `'t'/'f'` → `TRUE/FALSE` | 6.248 |
| R05 | `"1.5 shared baths"` → `bathrooms=1.5`, `bathroom_shared=TRUE` (si no lo dice → NULL) | 6.231 |
| R06 | Coordenadas a 6 decimales | 4.858 |
| R07–R09 | Quitar etiquetas HTML `<br />` | 5.029 / 3.539 / 100.809 |
| R10 | Antigüedad "años + meses" → meses totales | 3.094 hosts |
| R11–R12 | `min_nights > max_nights` → ambos NULL | 2 / 763 |
| R13 | Lista JSON de amenities → filas | 6.246 |
| R15 | Reviewer con 2 nombres → el de su reseña más reciente | 2 |
| R16 | Reseña repetida → se guarda una vez | 13.362 |

**Cómo ejecutarlo.**
```bash
python scripts/etl.py --simulate-error   # DEMO de ROLLBACK
python scripts/etl.py                    # carga real (~2 min)
```

**Resultado.** **Demostración del ROLLBACK** (salida real): después de cargar las 11 tablas, el script
inserta a propósito una reseña de un anuncio inexistente:
```
ERROR: ForeignKeyViolation: insert or update on table "listing_review" violates foreign key constraint
ROLLBACK ejecutado. Comprobamos que no ha quedado nada cargado:
    listing          0 filas
    calendar_day     0 filas
    ...
```
Carga real: 3,7 millones de filas en unos 135 s.

**Qué decir si preguntan.** Detalle curioso para la presentación: tras el ROLLBACK, los ids `IDENTITY` de `province`
empiezan en 4 y no en 1. **Las secuencias no son transaccionales**: los números consumidos
durante la transacción fallida no se devuelven. Es el comportamiento normal de PostgreSQL.

---

## Paso 6 - Verificar las restricciones después de la carga

**Objetivo.** Enseñar en pgAdmin que todas las restricciones siguen existiendo tras la carga.

**Cómo ejecutarlo.** Abrir **[`sql/verify_constraints.sql`](../sql/verify_constraints.sql)** en el Query Tool de pgAdmin:
1. lista cada restricción con su definición (`pg_constraint`), lo que sirve de **captura para el informe**;
2. resumen por tipo;
3. sentencias comentadas que **deben fallar** (FK, CHECK, UNIQUE, NOT NULL) dentro de un `BEGIN … ROLLBACK`;
4. filas por tabla.

**Índices** - [`sql/index_demo.sql`](../sql/index_demo.sql) mide la misma consulta con y sin
índice. Usa un truco: en PostgreSQL hasta `DROP INDEX` es transaccional, así que se borra,
se mide y con `ROLLBACK` el índice vuelve. Resultados reales:

| Consulta | Con índice | Sin índice |
|---|---|---|
| reseñas de un reviewer (419.594 filas) | 1,5 ms (Index Scan) | 152 ms (Parallel Seq Scan) |
| disponibilidad de un día (2,28 M filas) | 41 ms | 380 ms |

---

## Paso 7 - Las 13 consultas SQL

**Objetivo.** Al menos 10 consultas; cada miembro firma al menos 2 avanzadas. Entre todas deben aparecer:
JOIN, GROUP BY + HAVING, subconsulta, función ventana, CTE e INSERT/UPDATE/DELETE en transacción.

**Qué se hizo.** Una consulta por fichero en `sql/queries/`. La cabecera de cada fichero tiene autor, pregunta,
por qué importa, técnicas y parámetros por defecto. `scripts/run_queries.py` las ejecuta y genera
**[`docs/queries_results.md`](queries_results.md)** con el formato que pide el enunciado
(pregunta, SQL, muestra del resultado y por qué es relevante).

| ID | Autor | Pregunta (resumen) | Técnicas obligatorias |
|---|---|---|---|
| Q01 | Aitor | Precio mediano por municipio | JOIN 3 tablas, **GROUP BY + HAVING** |
| Q02 | Aitor | Anuncios más reseñados por provincia | **CTE**, **RANK() OVER (PARTITION BY)** |
| Q03 | Aitor | Reseñas por mes y variación interanual | CTE encadenadas, generate_series, **LAG(…,12)** |
| Q04 | Aitor | Anfitriones con más anuncios (concentración) | HAVING, **subconsulta escalar** |
| Q05 | Iker | % de días no disponibles los próximos 12 meses | CTE sobre los 2,3 M de filas |
| Q06 | Iker | Prima de precio por servicio (amenity) | CTE, JOIN por la tabla N:M, HAVING |
| Q07 | Iker | Superhosts vs anfitriones normales | **subconsulta correlacionada** |
| Q08 | Iker | Ocupación fin de semana vs entre semana | CTE, FILTER, HAVING, RANK() |
| Q09 | Aitor | ¿Qué pasa si suben los precios un X %? | **UPDATE dentro de transacción + ROLLBACK** |
| Q10 | Iker | Huéspedes que repiten | **LEAD()**, SUM(COUNT(*)) OVER () |
| Q11 | Aitor | Anuncios sin número de registro turístico | GROUP BY + HAVING, FILTER |
| Q12 | Iker | Gangas: más baratos que su municipio y bien puntuados | dos CTE (mediana con percentile_cont, reseñas por anuncio) |
| Q13 | Aitor | Mapa de anuncios por quintil de precio | **NTILE(5)**, MIN/MAX OVER (PARTITION BY), subconsulta en FROM |

> **Pendiente.** El reparto de autores es una **propuesta**: cada uno debe revisar, entender y poder
> explicar sus consultas (y las del otro).

**Algunos resultados interesantes** (para la historia de la presentación):
- Donostia tiene un precio mediano de **228 €/noche** con 1.395 anuncios; Bilbao es mucho más barato.
- Los superhosts puntúan unas **0,18 estrellas más** en las tres provincias.
- El **91,8 %** de los huéspedes solo escribe una reseña en Euskadi.
- Laguardia y Bilbao tienen la mayor diferencia de ocupación entre fin de semana y entre semana (unos 14–18 puntos).
- En Gernika-Lumo y Karrantza la mitad de los anuncios **no muestra número de registro**.

**Qué decir si preguntan.** Sobre la seguridad: los valores del usuario van en `%(province)s` y se pasan aparte a
`cursor.execute(sql, params)`. Comprobado: `province = "Vizcaya' OR '1'='1"` devuelve 0 filas, y
`"x'; DROP TABLE airbnb.listing; --"` no borra nada.

---

## Paso 8 - Visualización con Streamlit

**Objetivo.** Al menos 4 gráficos alimentados por las consultas, filtros que viajan a SQL como parámetros,
ningún SQL escrito por el usuario y nada de cuelgues con entradas inválidas.

**Qué se hizo.** `app/app.py`:
- **Un mapa, 10 gráficos y 3 tablas**, organizados en 7 pestañas (Mapa, Precios, Demanda,
  Anfitriones, Servicios y licencias, Huéspedes, Simulación de precios).
- Diseño sobrio, sin iconos: paleta categórica fija (cada provincia tiene siempre el mismo color),
  rampa de un solo tono azul para magnitudes (quintiles de precio del mapa), barras finas y rejilla
  discreta, siguiendo una guía de visualización de datos.
- Filtros globales (provincia, tipo de alojamiento) y filtros por gráfico (sliders). Todos se
  pasan como parámetros a la consulta.
- Los desplegables solo ofrecen valores válidos, y sus listas salen también de SQL.
- Cada consulta va en `try/except`: un error de base de datos se muestra como mensaje y la app no se cae.
- Debajo de cada gráfico, un desplegable muestra el SQL exacto, las técnicas usadas y el autor.
- Pestaña **Simulación de precios**: ejecuta el UPDATE de Q09 en una transacción y hace ROLLBACK.
- `pandas` **solo** se usa como contenedor de las filas devueltas para dárselas a Plotly. No se
  filtra, agrupa ni calcula nada en Python.

**Cómo ejecutarlo.** `streamlit run app/app.py` → http://localhost:8501

---

## Paso 9 - Repositorio y entrega

- GitHub: repositorio privado (los datos no se suben, ver `.gitignore`).
- Para reproducir todo desde cero: `python scripts/run_all.py`.
- Pendiente para el informe PDF: capturas de pgAdmin y de la app, el ER en la notación del
  curso, el registro de esfuerzo (`docs/effort_log.md`) y la tabla de uso de IA (`docs/ai_adoption.md`).
