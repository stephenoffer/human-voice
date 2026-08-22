# Postmortem: elevated error rates in the checkout service

## Summary

On March 14 between 09:12 and 11:47 UTC, the checkout service returned HTTP 500
for approximately 4.2% of requests. The root cause was a connection pool
exhaustion issue in the payment gateway client, triggered by a configuration
change that reduced the pool size from 50 to 20 connections. The change was
deployed as part of a routine resource optimization effort, allowing us to
reduce memory consumption across the fleet.

## Timeline

The configuration change was merged on March 13 and deployed to production the
following morning. What made the failure difficult to diagnose is that the
reduced pool size was sufficient under normal traffic, and it only became
insufficient once the morning peak arrived. Error rates began climbing at 09:12
and the first alert fired at 09:24, giving the on-call engineer a twelve-minute
window before the page.

Initial investigation focused on the payment gateway itself, since the errors
were surfacing at the integration boundary. It was only after we ruled out an
upstream incident that attention turned to our own client configuration. The
reason this took forty minutes is that our dashboards surface gateway latency
but not pool saturation, leaving the team without the signal that would have
pointed directly at the cause.

## Contributing factors

The change was reviewed and approved by two engineers, neither of whom had
context on the peak traffic profile. Our load testing environment runs at
roughly 30% of production volume, meaning the reduced pool size passed
validation without incident. The runbook for the checkout service does not
mention connection pooling, so the on-call engineer had no reason to check it
early.

## What we are changing

We are restoring the pool size to 50 and adding a saturation metric to the
service dashboard, ensuring that the next occurrence is visible within seconds
rather than requiring inference from latency. We are also updating our load
testing configuration to replay peak traffic profiles, which will catch
capacity regressions before they reach production. Finally, the runbook is
being expanded to include resource limits, giving future responders a checklist
that reflects how the service actually fails.
