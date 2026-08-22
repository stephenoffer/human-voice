Subject: Update on the reporting migration

Hi team,

Wanted to give everyone a quick status update on the reporting migration ahead of Thursday's review.

The data pipeline is complete and running in parallel with the old system. We have been comparing outputs daily for the past two weeks and the numbers now match within rounding on every report except the attribution summary, which is off by roughly 2% because the new system attributes to the first touch rather than the last. That is a definitional change rather than a bug, but it will surprise anyone who compares the two directly, so we should decide before launch whether to match the old behavior or communicate the change.

Remaining work is the permissions layer and the scheduled export. Both are in progress and I expect them done by the end of next week, which leaves a buffer before the planned cutover.

One thing I would like input on Thursday: whether we keep the old dashboards available read-only for a month after cutover. It costs us some maintenance but it makes the transition much less disruptive for the finance team.

Thanks,
Priya
