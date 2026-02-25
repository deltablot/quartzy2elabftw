-- ===============================
-- DEDUPLICATE QUARTZY ITEMS
-- ===============================
SET autocommit = 0;
START TRANSACTION;

CREATE TEMPORARY TABLE dedup_map AS
SELECT
    i.id AS duplicate_id,
    MIN(i2.id) AS original_id
FROM items i
    JOIN items i2
        ON JSON_UNQUOTE(JSON_EXTRACT(i.metadata, '$.extra_fields."Quartzy ID".value'))
        = JSON_UNQUOTE(JSON_EXTRACT(i2.metadata, '$.extra_fields."Quartzy ID".value'))
WHERE JSON_EXTRACT(i.metadata, '$.extra_fields."Quartzy ID".value') IS NOT NULL
GROUP BY i.id
HAVING duplicate_id <> original_id;

UPDATE experiments2items e
    JOIN dedup_map d ON e.link_id = d.duplicate_id
    SET e.link_id = d.original_id;

DELETE i
FROM items i
JOIN dedup_map d ON i.id = d.duplicate_id;

COMMIT;
