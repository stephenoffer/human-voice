# Setting up automated database backups

Nightly backups for a single-server PostgreSQL install, stored off the machine.
Assumes shell access and the ability to install packages.

Start by creating a role with read access and nothing else. Backing up as superuser
works fine right up until the script is compromised, at which point the database is
too.

Dump with `pg_dump` in the custom format, which compresses and supports parallel
restore. Write to a local staging directory rather than piping straight to remote
storage. Pipe it and a dropped connection leaves you a truncated file that exited
zero.

Then get it off the box. A backup on the same disk as the database is not a backup.
Sync the staging directory to object storage and turn on bucket versioning, so a bug
in your own script can't overwrite your history.

Put it in cron, then add a check that alerts when the newest backup is older than it
should be. Backup failures are almost always silent. A schedule nobody watches is a
schedule you shouldn't trust.

Last, restore it. Into a scratch database, then run a few queries. Until you've done
that once, you don't have backups. You have files.
