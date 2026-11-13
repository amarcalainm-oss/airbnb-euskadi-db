-- =====================================================================
--  Demostración: ¿cuánto ayuda un índice en la tabla grande?
--  En PostgreSQL hasta el DROP INDEX es transaccional: lo borramos dentro
--  de una transacción, medimos, y con ROLLBACK el índice vuelve a existir.
--  Ejecutar en pgAdmin y comparar "Execution Time" de los dos planes.
-- =====================================================================
BEGIN;

-- (a) CON índice idx_review_reviewer: todas las reseñas de un reviewer
EXPLAIN ANALYZE
SELECT * FROM airbnb.review WHERE reviewer_id = 27989262;

-- (b) SIN índice: PostgreSQL tiene que leer las 419.594 reseñas (Seq Scan)
DROP INDEX airbnb.idx_review_reviewer;
EXPLAIN ANALYZE
SELECT * FROM airbnb.review WHERE reviewer_id = 27989262;

ROLLBACK;   -- el índice vuelve a existir

BEGIN;
-- (c) CON idx_calendar_day: disponibilidad de un día concreto en 2,28 M filas
EXPLAIN ANALYZE
SELECT COUNT(*) FILTER (WHERE available) FROM airbnb.calendar_day WHERE day = DATE '2026-12-31';

-- (d) SIN índice
DROP INDEX airbnb.idx_calendar_day;
EXPLAIN ANALYZE
SELECT COUNT(*) FILTER (WHERE available) FROM airbnb.calendar_day WHERE day = DATE '2026-12-31';
ROLLBACK;
