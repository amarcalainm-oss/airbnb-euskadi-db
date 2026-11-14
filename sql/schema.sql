DROP SCHEMA IF EXISTS airbnb CASCADE;
CREATE SCHEMA airbnb;
SET search_path TO airbnb;

CREATE TABLE province (
    province_id   SMALLINT     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE municipality (
    municipality_id  INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             VARCHAR(150) NOT NULL UNIQUE,
    province_id      SMALLINT     NOT NULL REFERENCES province(province_id)
);

CREATE TABLE host (
    host_id               BIGINT       PRIMARY KEY,
    host_profile_id       BIGINT       NOT NULL UNIQUE,
    name                  VARCHAR(100) NOT NULL,
    location              VARCHAR(150),
    about                 TEXT,
    is_superhost          BOOLEAN      NOT NULL,
    has_profile_pic       BOOLEAN      NOT NULL,
    identity_verified     BOOLEAN      NOT NULL,
    listings_count        INTEGER      NOT NULL CHECK (listings_count >= 0),  -- en todo Airbnb, no solo Euskadi
    months_as_host        SMALLINT     NOT NULL CHECK (months_as_host >= 0),
    months_as_user        SMALLINT     NOT NULL CHECK (months_as_user >= 0),
    CHECK (months_as_host <= months_as_user)
);

CREATE TABLE property_type (
    property_type_id  SMALLINT     GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name              VARCHAR(60)  NOT NULL UNIQUE
);

CREATE TABLE listing (
    listing_id         BIGINT        PRIMARY KEY,
    host_id            BIGINT        NOT NULL REFERENCES host(host_id),
    municipality_id    INTEGER       NOT NULL REFERENCES municipality(municipality_id),
    property_type_id   SMALLINT      NOT NULL REFERENCES property_type(property_type_id),
    name               VARCHAR(100)  NOT NULL,
    description        TEXT,
    latitude           NUMERIC(8,6)  NOT NULL CHECK (latitude  BETWEEN 42.0 AND 44.0),   -- límites de Euskadi
    longitude          NUMERIC(9,6)  NOT NULL CHECK (longitude BETWEEN -4.0 AND -1.0),
    room_type          VARCHAR(20)   NOT NULL
                       CHECK (room_type IN ('Entire home/apt', 'Private room', 'Hotel room', 'Shared room')),
    accommodates       SMALLINT      NOT NULL CHECK (accommodates > 0),
    bathrooms          NUMERIC(3,1)  CHECK (bathrooms >= 0),
    bathroom_shared    BOOLEAN,
    bathrooms_text     VARCHAR(30),
    bedrooms           SMALLINT      CHECK (bedrooms >= 0),
    beds               SMALLINT      CHECK (beds >= 0),
    price              NUMERIC(10,2) CHECK (price > 0),                -- EUR por noche
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

CREATE TABLE amenity (
    amenity_id   INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE listing_amenity (
    listing_id   BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    amenity_id   INTEGER  NOT NULL REFERENCES amenity(amenity_id),
    PRIMARY KEY (listing_id, amenity_id)
);

CREATE TABLE calendar_day (
    listing_id      BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    day             DATE     NOT NULL,
    available       BOOLEAN  NOT NULL,
    minimum_nights  INTEGER  CHECK (minimum_nights > 0),
    maximum_nights  INTEGER  CHECK (maximum_nights > 0),
    PRIMARY KEY (listing_id, day),
    CHECK (minimum_nights <= maximum_nights)
);

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

-- Una reseña puede mostrarse en varios anuncios
CREATE TABLE listing_review (
    listing_id    BIGINT   NOT NULL REFERENCES listing(listing_id) ON DELETE CASCADE,
    review_id     BIGINT   NOT NULL REFERENCES review(review_id),
    PRIMARY KEY (listing_id, review_id)
);

CREATE INDEX idx_municipality_province  ON municipality(province_id);
CREATE INDEX idx_listing_host           ON listing(host_id);
CREATE INDEX idx_listing_municipality   ON listing(municipality_id);
CREATE INDEX idx_listing_property_type  ON listing(property_type_id);
CREATE INDEX idx_listing_amenity_amen   ON listing_amenity(amenity_id);
CREATE INDEX idx_calendar_day           ON calendar_day(day);
CREATE INDEX idx_review_reviewer        ON review(reviewer_id);
CREATE INDEX idx_review_date            ON review(review_date);
CREATE INDEX idx_listing_review_review  ON listing_review(review_id);
