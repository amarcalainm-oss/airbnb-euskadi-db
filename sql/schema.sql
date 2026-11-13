-- =====================================================================
--  Esquema físico - Airbnb Euskadi (Inside Airbnb, scrape 25-09-2026)
--  Se ejecuta ANTES de la carga. La carga (scripts/etl.py) solo inserta filas.
--
--  Modelo (ver docs/modelo.md):
--    province 1──N municipality 1──N listing N──1 host
--    listing N──1 property_type
--    listing N──M amenity        (tabla puente listing_amenity)
--    listing 1──N calendar_day   (entidad débil: PK = listing + fecha)
--    listing N──M review         (tabla puente listing_review, ver nota)
--    reviewer 1──N review
-- =====================================================================

DROP SCHEMA IF EXISTS airbnb CASCADE;
CREATE SCHEMA airbnb;
SET search_path TO airbnb;

-- ---------------------------------------------------------------------
-- PROVINCE: las 3 provincias (neighbourhood_group). Tabla de 3 filas,
-- pero evita repetir el texto en 255 municipios y garantiza que no haya
-- variantes mal escritas ('GuipÃºzcoa' vs 'Guipúzcoa').
-- ---------------------------------------------------------------------
CREATE TABLE province (
    province_id   SMALLINT     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- MUNICIPALITY: los 255 municipios de neighbourhoods.csv.
-- El nombre es único en el fichero (comprobado en el perfilado) => UNIQUE.
-- ---------------------------------------------------------------------
CREATE TABLE municipality (
    municipality_id  INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             VARCHAR(150) NOT NULL UNIQUE,
    province_id      SMALLINT     NOT NULL REFERENCES province(province_id)
);

-- ---------------------------------------------------------------------
-- HOST: anfitriones. En listings.csv cada host_id tiene SIEMPRE los mismos
-- atributos (dependencia funcional comprobada) => se normaliza aquí (3FN).
-- Las fechas host_since, response_rate... vienen 100% vacías: no se crean.
-- ---------------------------------------------------------------------
CREATE TABLE host (
    host_id               BIGINT       PRIMARY KEY,
    host_profile_id       BIGINT       NOT NULL UNIQUE,
    name                  VARCHAR(100) NOT NULL,
    location              VARCHAR(150),
    about                 TEXT,
    is_superhost          BOOLEAN      NOT NULL,
    has_profile_pic       BOOLEAN      NOT NULL,
    identity_verified     BOOLEAN      NOT NULL,
    listings_count        INTEGER      NOT NULL CHECK (listings_count >= 0),  -- en TODO Airbnb, no solo Euskadi
    months_as_host        SMALLINT     NOT NULL CHECK (months_as_host >= 0),
    months_as_user        SMALLINT     NOT NULL CHECK (months_as_user >= 0),
    CHECK (months_as_host <= months_as_user)
);

-- ---------------------------------------------------------------------
-- PROPERTY_TYPE: 64 tipos de alojamiento ('Entire condo', 'Room in hotel'...)
-- ---------------------------------------------------------------------
CREATE TABLE property_type (
    property_type_id  SMALLINT     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name              VARCHAR(60)  NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- LISTING: el anuncio. Columnas derivables de otras tablas NO se guardan
-- (number_of_reviews, first/last_review, reviews_per_month,
--  calculated_host_listings_count*, availability_*, *_minimum_nights...):
-- se calculan con SQL cuando hacen falta. Ver docs/modelo.md.
-- ---------------------------------------------------------------------
CREATE TABLE listing (
    listing_id         BIGINT        PRIMARY KEY,
    host_id            BIGINT        NOT NULL REFERENCES host(host_id),
    municipality_id    INTEGER       NOT NULL REFERENCES municipality(municipality_id),
    property_type_id   SMALLINT      NOT NULL REFERENCES property_type(property_type_id),
    name               VARCHAR(100)  NOT NULL,
    description        TEXT,
    latitude           NUMERIC(8,6)  NOT NULL CHECK (latitude  BETWEEN 42.0 AND 44.0),   -- caja de Euskadi
    longitude          NUMERIC(9,6)  NOT NULL CHECK (longitude BETWEEN -4.0 AND -1.0),
    room_type          VARCHAR(20)   NOT NULL
                       CHECK (room_type IN ('Entire home/apt', 'Private room', 'Hotel room', 'Shared room')),
    accommodates       SMALLINT      NOT NULL CHECK (accommodates > 0),
    bathrooms          NUMERIC(3,1)  CHECK (bathrooms >= 0),          -- extraído de bathrooms_text
    bathroom_shared    BOOLEAN,                                        -- extraído de bathrooms_text
    bathrooms_text     VARCHAR(30),                                    -- texto original
    bedrooms           SMALLINT      CHECK (bedrooms >= 0),
    beds               SMALLINT      CHECK (beds >= 0),
    price              NUMERIC(10,2) CHECK (price > 0),                -- precio por noche (EUR, el CSV usa '$')
    minimum_nights     INTEGER       CHECK (minimum_nights > 0),
    maximum_nights     INTEGER       CHECK (maximum_nights > 0),
    has_availability   BOOLEAN,
    score_rating       NUMERIC(3,2)  CHECK (score_rating        BETWEEN 0 AND 5),
    score_accuracy     NUMERIC(3,2)  CHECK (score_accuracy      BETWEEN 0 AND 5),
    score_cleanliness  NUMERIC(3,2)  CHECK (score_cleanliness   BETWEEN 0 AND 5),
    score_checkin      NUMERIC(3,2)  CHECK (score_checkin       BETWEEN 0 AND 5),
    score_communication NUMERIC(3,2) CHECK (score_communication BETWEEN 0 AND 5),
    score_location     NUMERIC(3,2)  CHECK (score_location      BETWEEN 0 AND 5),
    score_value        NUMERIC(3,2)  CHECK (score_value         BETWEEN 0 AND 5),
    license            VARCHAR(200),
    estimated_occupancy_l365d SMALLINT      CHECK (estimated_occupancy_l365d BETWEEN 0 AND 366),
    estimated_revenue_l365d   NUMERIC(10,2) CHECK (estimated_revenue_l365d >= 0),
    source             VARCHAR(20)   CHECK (source IN ('previous scrape')),
    last_scraped       DATE          NOT NULL,
    CHECK (minimum_nights <= maximum_nights)
);

-- ---------------------------------------------------------------------
-- AMENITY + LISTING_AMENITY: en el CSV los servicios vienen como una lista
-- JSON dentro de una sola celda (viola la 1FN). Se separan en una relación N:M.
-- ---------------------------------------------------------------------
CREATE TABLE amenity (
    amenity_id   INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE listing_amenity (
    listing_id   BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    amenity_id   INTEGER  NOT NULL REFERENCES amenity(amenity_id),
    PRIMARY KEY (listing_id, amenity_id)
);

-- ---------------------------------------------------------------------
-- CALENDAR_DAY: entidad débil de LISTING (un registro por anuncio y día,
-- 365 días desde el scrape). Es la tabla grande: ~2,28 millones de filas.
-- ---------------------------------------------------------------------
CREATE TABLE calendar_day (
    listing_id      BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    day             DATE     NOT NULL,
    available       BOOLEAN  NOT NULL,
    minimum_nights  INTEGER  CHECK (minimum_nights > 0),
    maximum_nights  INTEGER  CHECK (maximum_nights > 0),
    PRIMARY KEY (listing_id, day),
    CHECK (minimum_nights <= maximum_nights)
);

-- ---------------------------------------------------------------------
-- REVIEWER, REVIEW, LISTING_REVIEW
-- Excepción justificada: en reviews.csv el mismo review id aparece en
-- varios anuncios (8.074 ids, siempre del mismo anfitrión, con fecha,
-- autor y texto idénticos). Es UNA reseña que Airbnb muestra en varios
-- anuncios agrupados. Por eso la reseña se guarda una vez (review) y la
-- relación con los anuncios es N:M (listing_review).
-- ---------------------------------------------------------------------
CREATE TABLE reviewer (
    reviewer_id   BIGINT       PRIMARY KEY,
    name          VARCHAR(60)  NOT NULL
);

CREATE TABLE review (
    review_id     BIGINT   PRIMARY KEY,
    reviewer_id   BIGINT   NOT NULL REFERENCES reviewer(reviewer_id),
    review_date   DATE     NOT NULL CHECK (review_date >= DATE '2008-01-01'),  -- Airbnb nace en 2008
    comments      TEXT     NOT NULL
);

CREATE TABLE listing_review (
    listing_id    BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    review_id     BIGINT   NOT NULL REFERENCES review(review_id),
    PRIMARY KEY (listing_id, review_id)
);

-- ---------------------------------------------------------------------
-- Índices sobre claves foráneas (PostgreSQL NO los crea automáticamente).
-- Las PK y UNIQUE ya llevan índice propio.
-- ---------------------------------------------------------------------
CREATE INDEX idx_municipality_province  ON municipality(province_id);
CREATE INDEX idx_listing_host           ON listing(host_id);
CREATE INDEX idx_listing_municipality   ON listing(municipality_id);
CREATE INDEX idx_listing_property_type  ON listing(property_type_id);
CREATE INDEX idx_listing_amenity_amen   ON listing_amenity(amenity_id);
CREATE INDEX idx_calendar_day           ON calendar_day(day);
CREATE INDEX idx_review_reviewer        ON review(reviewer_id);
CREATE INDEX idx_review_date            ON review(review_date);
CREATE INDEX idx_listing_review_review  ON listing_review(review_id);
