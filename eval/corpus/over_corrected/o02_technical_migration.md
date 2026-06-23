migrating the auth service off the monolith. honestly? long overdue.

we're moving session handling into its own deployment. the token signing key becomes the load-bearing dependency, so rotate it carefully. idk how the old code survived this long tbh.

step one. stand up the new service behind a sidecar. step two. dual-write sessions. step three. cut reads over. step four. delete the old path, fr.

ngl the rollback story is the scary part. if dual-write drifts, you get split sessions and users get logged out at random. lol no.

we tested the cutover in staging twice. it's giving stable. no notes.

watch the connection pool. the new service opens its own, so bump the postgres max_connections or you'll starve everything else. smh, learned that the hard way.

ship it monday. ramp slow.
