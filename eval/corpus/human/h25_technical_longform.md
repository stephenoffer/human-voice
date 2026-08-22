# Why we stopped using feature flags for schema changes

We had a rule for four years: every risky change goes behind a flag. It worked
for UI and it worked for API behavior. For database schema it slowly turned
into a mess, and it took a bad Thursday in October for us to admit it.

The pattern was this. Add a column, write to both old and new, flip a flag to
read from the new one, backfill, remove the old. Five steps, each behind a
config value, each requiring the flag service to be up and correct. On the
Thursday in question the flag service returned defaults for about ninety
seconds during a deploy. Half the fleet read the old column, half read the new,
and we spent the rest of the day reconciling 40,000 rows by hand.

The thing that made this worse than it needed to be: nobody owned the flag
after step three. The engineer who added it moved teams. The flag stayed. We
had eleven schema flags in the codebase, six of them past their useful life,
and no way to tell from the code which was which.

What we do now is not clever. Schema changes go through expand-migrate-contract
with no runtime switch at all. Expand ships. Migration runs as a job with its
own logging. Contract ships a week later, after somebody has actually looked at
the numbers. It is slower. Three deploys instead of one, spread across days
instead of hours.

Slower turned out to be fine. The migrations we were most afraid of are the
ones where being forced to wait a week caught something. Twice now the
backfill job has surfaced data we did not know existed, which under the old
scheme would have been discovered by a customer.

Flags are still everywhere else. I would defend them for anything a user can
see. The argument for schema is different because the failure mode is
different: a UI flag that misbehaves shows the wrong button, and a schema flag
that misbehaves writes to the wrong place, and you cannot flip your way out of
that.
