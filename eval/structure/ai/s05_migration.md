# Migration Plan: Moving User Profiles from MongoDB to PostgreSQL

## Purpose

This document outlines the plan for migrating user profile data from MongoDB to PostgreSQL. The migration will improve data consistency, simplify reporting, and reduce operational costs by consolidating onto a single database platform.

## Schema Design

The `profiles` collection currently holds 18.4M documents with an average size of 3.1 KB. Documents have drifted over five years: 212 distinct top-level key combinations appear in a 1% sample, and 7% of documents store `address` as a string instead of an embedded object. The target schema normalizes the stable fields and keeps the long tail in a `jsonb` column.

```sql
CREATE TABLE users (
  id            uuid PRIMARY KEY,
  legacy_oid    char(24) UNIQUE NOT NULL,
  email         citext UNIQUE NOT NULL,
  display_name  text,
  created_at    timestamptz NOT NULL,
  updated_at    timestamptz NOT NULL
);

CREATE TABLE user_addresses (
  user_id   uuid REFERENCES users(id) ON DELETE CASCADE,
  kind      text CHECK (kind IN ('billing', 'shipping')),
  line1     text, line2 text, city text, region text,
  postcode  text, country char(2),
  PRIMARY KEY (user_id, kind)
);

CREATE TABLE user_attributes (
  user_id   uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  extra     jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX user_attributes_extra_gin ON user_attributes USING gin (extra jsonb_path_ops);
```

`legacy_oid` keeps the Mongo `_id` so services can dual-read during cutover. String addresses are parsed with `libpostal` in the backfill; the 0.4% that fail parsing land in `user_attributes.extra->'raw_address'` and are listed in `migration_reports.unparsed_addresses` for support to review. Emails are lowercased and deduplicated before insert: the sample found 3,912 case-variant duplicates, which the backfill resolves by keeping the document with the latest `lastLoginAt` and writing the others to `migration_reports.merged_accounts`.

The backfill runs as a Spark job reading from a hidden secondary with `readConcern: "majority"`, in 500k-document chunks keyed by `_id` range, writing via `COPY` into staging tables and then `INSERT ... ON CONFLICT (legacy_oid) DO UPDATE`. A change stream consumer started before the backfill captures writes that happen during it and replays them afterwards, so the two converge without a write freeze. At 9k documents per second the full backfill takes about 35 minutes.

## Testing

We will test the migration thoroughly.

## Rollback

If something goes wrong, we will roll back.

## Timeline

The migration will be completed in the next quarter.

## Risks

There are some risks involved.

## Conclusion

This migration will improve data consistency, simplify reporting, and reduce operational costs by consolidating user profile data onto PostgreSQL.
