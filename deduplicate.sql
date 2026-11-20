-- ===============================
-- DEDUPLICATE QUARTZY ITEMS
-- Quartzy duplicate cleanup for eLabFTW 6.0 (MySQL 8).
-- Stop the Quartzy cron/sync and BACK UP THE DATABASE before running
-- Keeps the earliest active item per (team, Quartzy ID)
-- Only removes duplicate items created since 2026-09-02 that have no
-- other user-facing data. Experiment links are moved to the kept item
-- Revisions/changelog of deleted items are removed by FK cascades.
-- =============================== FOR EE
-- I kept it DRY RUN by default (just in case..): change the final ROLLBACK to COMMIT after reviewing (line ~102)
-- ===============================

DROP TEMPORARY TABLE IF EXISTS dedup_map;
CREATE TEMPORARY TABLE dedup_map AS
SELECT i.id AS duplicate_id, originals.keep_id
FROM items i
JOIN (
    SELECT team,
           JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.extra_fields."Quartzy ID".value')) AS quartzy_id,
           MIN(id) AS keep_id
    FROM items
    WHERE state = 1
      AND JSON_TYPE(JSON_EXTRACT(metadata, '$.extra_fields."Quartzy ID".value')) IN ('STRING', 'INTEGER')
      AND JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.extra_fields."Quartzy ID".value')) <> ''
    GROUP BY team, quartzy_id
    HAVING COUNT(*) > 1
) originals ON originals.team = i.team
    AND originals.quartzy_id = JSON_UNQUOTE(JSON_EXTRACT(i.metadata, '$.extra_fields."Quartzy ID".value'))
WHERE i.id <> originals.keep_id AND i.state = 1;

-- Protect anything with manual changes or links other than experiment links
DROP TEMPORARY TABLE IF EXISTS safe_duplicates;
CREATE TEMPORARY TABLE safe_duplicates AS
SELECT d.duplicate_id, d.keep_id
FROM dedup_map d
JOIN items i ON i.id = d.duplicate_id
JOIN items kept ON kept.id = d.keep_id
WHERE i.created_at >= '2026-09-02'
  AND i.userid = kept.userid
  AND i.category <=> kept.category
  AND i.locked = 1 AND i.signature_count = 0 AND i.timestamped = 0
  AND i.is_bookable = 0 AND i.is_procurable = 0
  AND (i.lastchangeby IS NULL OR i.lastchangeby = i.userid)
  AND NOT EXISTS (SELECT 1 FROM uploads u WHERE u.item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM items_comments c WHERE c.item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM items_steps s WHERE s.item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM tags2entity t WHERE t.item_id = i.id AND t.item_type = 'items')
  AND NOT EXISTS (SELECT 1 FROM items2items l WHERE l.item_id = i.id OR l.link_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM items2experiments l WHERE l.item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM items_types2items l WHERE l.link_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM experiments_templates2items l WHERE l.link_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM compounds2items c WHERE c.entity_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM pin_items2users p WHERE p.entity_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM items_edit_mode e WHERE e.entity_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM team_events e WHERE e.item_link = i.id);

-- Review these counts before committing. For a fresh 3x local import, on my instance (1300 items per fetch)
-- expected duplicate_rows = safe_to_remove = 2600 and skipped = 0
SELECT (SELECT COUNT(*) FROM items) AS items_before,
       COUNT(*) AS duplicate_rows,
       COUNT(s.duplicate_id) AS safe_to_remove,
       COUNT(*) - COUNT(s.duplicate_id) AS skipped_for_review
FROM dedup_map d
LEFT JOIN safe_duplicates s ON s.duplicate_id = d.duplicate_id;

-- Show any protected duplicates (must be investigated separately)
SELECT d.duplicate_id, d.keep_id, i.title
FROM dedup_map d
JOIN items i ON i.id = d.duplicate_id
LEFT JOIN safe_duplicates s ON s.duplicate_id = d.duplicate_id
WHERE s.duplicate_id IS NULL
LIMIT 20;

START TRANSACTION;

-- Preserve experiment links. IGNORE handles links already on the kept item
INSERT IGNORE INTO experiments2items (item_id, link_id)
SELECT e.item_id, s.keep_id
FROM experiments2items e
JOIN safe_duplicates s ON s.duplicate_id = e.link_id;

-- Verify there are NO experiment links missing from the kept item
SELECT COUNT(*) AS missing_experiment_links_must_be_zero
FROM experiments2items e
JOIN safe_duplicates s ON s.duplicate_id = e.link_id
LEFT JOIN experiments2items kept ON kept.item_id = e.item_id AND kept.link_id = s.keep_id
WHERE kept.item_id IS NULL;

-- Remove an old link only if the new one actually exists
DELETE old FROM experiments2items old
JOIN safe_duplicates s ON s.duplicate_id = old.link_id
JOIN experiments2items kept ON kept.item_id = old.item_id AND kept.link_id = s.keep_id;

-- A duplicate with an unmoved experiment link is NOT deleted
DELETE i FROM items i
JOIN safe_duplicates s ON s.duplicate_id = i.id
LEFT JOIN experiments2items e ON e.link_id = i.id
WHERE e.link_id IS NULL;

SELECT COUNT(*) AS items_if_committed FROM items;

ROLLBACK; -- DRY RUN: change to COMMIT; ONLY after reviewing results and backup
SELECT COUNT(*) AS actual_items_after_transaction FROM items;

