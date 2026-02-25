## Deduplicate Quartzy Items Script

This SQL script removes duplicate `items` that share the same **Quartzy ID**.

For each Quartzy ID:
- The item with the smallest `id` is kept as the canonical entry.
- All `experiments2items` links referencing duplicate items are reassigned to the canonical item.
- Duplicate items are then deleted.
- All operations run inside a single database transaction.

### Usage

From inside MySQL:

```sql
SOURCE /full/path/to/deduplicate.sql;
```
