BEGIN;

EXPLAIN ANALYZE
SELECT * FROM airbnb.review WHERE reviewer_id = 27989262;

DROP INDEX airbnb.idx_review_reviewer;
EXPLAIN ANALYZE
SELECT * FROM airbnb.review WHERE reviewer_id = 27989262;

ROLLBACK;  -- DROP INDEX es transaccional: el índice vuelve

BEGIN;
EXPLAIN ANALYZE
SELECT COUNT(*) FILTER (WHERE available) FROM airbnb.calendar_day WHERE day = DATE '2026-12-31';

DROP INDEX airbnb.idx_calendar_day;
EXPLAIN ANALYZE
SELECT COUNT(*) FILTER (WHERE available) FROM airbnb.calendar_day WHERE day = DATE '2026-12-31';
ROLLBACK;
