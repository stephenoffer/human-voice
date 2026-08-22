Subject: Q3 platform migration — status and what we need from you

Hi team,

I wanted to share where the platform migration stands and flag two decisions
that need input before the end of the week.

We have completed the data migration for 14 of the 19 services, which puts us
slightly ahead of the schedule we set in June. What remains is the group of
services that share the legacy authentication layer, and these are the ones
that carry the real risk, since the cutover cannot be done incrementally.

The first decision is timing. We can either cut over the remaining services in
a single weekend window, accepting roughly six hours of degraded functionality,
or we can run both systems in parallel for two weeks, which eliminates the
downtime but doubles the operational burden on the on-call rotation during that
period. My recommendation is the single window, primarily because the parallel
approach requires us to maintain write consistency across two authentication
stores and that is where I expect us to find problems.

The second decision concerns the reporting integrations. Three customers have
built against the legacy API directly, and continuing to support it after the
migration means maintaining a translation layer indefinitely. Deprecating it
means giving those customers a deadline, which account management will need to
handle carefully.

Could you let me know your position on both by Thursday? Happy to walk through
the details on a call if that is easier.

Thanks,
Dana
