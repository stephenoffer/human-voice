# Setting up automated database backups

This guide covers configuring nightly backups for a PostgreSQL database running on a single server, with copies stored off-machine. It assumes you have shell access and can install packages.

## 1. Create a dedicated backup role

Create a database role with read access only. Using the superuser account for backups works, but it means a compromised backup script is a compromised database.

## 2. Write the dump script

Use `pg_dump` with the custom format, which supports parallel restore and compresses by default. Write to a local staging directory first rather than piping directly to remote storage, so that a network interruption does not leave you with a truncated file that looks successful.

## 3. Copy off the machine

A backup on the same disk as the database is not a backup. Sync the staging directory to object storage, and enable versioning on the bucket so that a script bug cannot overwrite your history.

## 4. Schedule and monitor

Add the script to cron, then add a check that alerts when the newest backup is older than expected. Most backup failures are silent, and a schedule you are not monitoring is a schedule you should not trust.

## 5. Test a restore

Restore into a scratch database and run a few queries against it. Until you have done this once, you have a backup process of unknown quality.
