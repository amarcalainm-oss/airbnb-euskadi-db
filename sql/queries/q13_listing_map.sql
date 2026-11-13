-- id: Q13
-- author: Aitor Marcalain
-- title: Map of listings by price quintile
-- question: Where are the listings located, and where are the cheapest and the most expensive fifths of the market concentrated?
-- why: Splitting the market into price fifths in SQL and placing every listing on the map shows how price varies with location: the coast and the three capitals against the inland municipalities.
-- techniques: JOIN, window functions NTILE(5) and MIN/MAX OVER (PARTITION BY), subquery in FROM
-- params: {"province": null, "room_type": null, "min_reviews": 0}
SELECT q.listing_id, q.listing, q.municipality, q.room_type, q.price, q.score_rating,
       q.latitude, q.longitude, q.price_quintile,
       'Q' || q.price_quintile || ': ' ||
       MIN(q.price) OVER (PARTITION BY q.price_quintile) || ' - ' ||
       MAX(q.price) OVER (PARTITION BY q.price_quintile) || ' EUR'      AS price_band
FROM (
    SELECT l.listing_id, l.name AS listing, m.name AS municipality, l.room_type, l.price,
           l.score_rating, l.latitude, l.longitude,
           NTILE(5) OVER (ORDER BY l.price) AS price_quintile
    FROM airbnb.listing l
    JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
    JOIN airbnb.province     p ON p.province_id     = m.province_id
    WHERE l.price IS NOT NULL
      AND (%(province)s  IS NULL OR p.name      = %(province)s)
      AND (%(room_type)s IS NULL OR l.room_type = %(room_type)s)
      AND (SELECT COUNT(*) FROM airbnb.listing_review lr WHERE lr.listing_id = l.listing_id) >= %(min_reviews)s
) q
ORDER BY q.price_quintile, q.price;
