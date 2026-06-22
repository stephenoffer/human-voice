# pgslice

Move old rows out of a hot Postgres table without locking it.

The problem this solves: your `events` table is 400GB, 95% of queries touch the last week, and `DELETE` on the old rows takes a lock that stalls writes. pgslice copies rows into monthly partition tables in small batches, verifies the counts match, then drops the originals in a transaction short enough that nobody notices.

Install with `pip install pgslice`. You point it at a table and a cutoff date:

    pgslice events --before 2024-01-01 --batch 5000

It defaults to a 5000-row batch and sleeps 100ms between batches so replication doesn't fall behind. On our prod database it moved 80 million rows over a weekend with the replica lag never crossing 200ms.

It will not touch a table without a primary key, and it refuses to run inside a transaction. Both of those are on purpose.
