Subject: Q3 platform migration — status and two decisions

Hi team,

Quick status on the migration, plus two things I need answers on by Thursday.

Data migration is done for 14 of 19 services, which puts us a little ahead of
the June schedule. The five left over all share the legacy auth layer, and
those are the risky ones, because we cannot cut them over one at a time.

First decision: timing. Either we do the remaining five in one weekend window
and accept roughly six hours of degraded functionality, or we run both systems
in parallel for two weeks with no downtime and double the on-call load. I would
take the weekend window. Running in parallel means keeping writes consistent
across two auth stores, and that is where I expect this to go wrong.

Second decision: the reporting integrations. Three customers built against the
legacy API directly. Keeping it alive means a translation layer we maintain
forever. Killing it means giving those three a deadline, which is a
conversation account management will need to run carefully.

Positions on both by Thursday would be great. Happy to talk it through on a
call if that is faster.

Thanks,
Dana
