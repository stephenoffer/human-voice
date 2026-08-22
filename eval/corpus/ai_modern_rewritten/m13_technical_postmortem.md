# Postmortem: elevated error rates in the checkout service

On March 14, checkout returned HTTP 500 for about 4.2% of requests between
09:12 and 11:47 UTC. We had shrunk the payment gateway client's connection pool
from 50 to 20 the day before, as part of a memory reduction pass. Twenty was
enough until the morning peak arrived.

Errors started at 09:12. The alert fired at 09:24, so on-call had twelve
minutes of climbing error rate before anyone looked. Because the failures
surfaced at the integration boundary, the first forty minutes went to ruling
out a gateway incident on the vendor's side. Our dashboards show gateway
latency. They do not show pool saturation, which is the one number that would
have ended the investigation immediately.

Two engineers reviewed the change. Neither of them had reason to know the peak
traffic profile, and our load test runs at roughly 30% of production volume, so
20 connections passed validation comfortably. The checkout runbook says nothing
about connection pooling. There was no path by which the responder was going to
check it early.

We have put the pool back to 50. A saturation metric goes on the service
dashboard this week, so the next occurrence shows up in seconds instead of
being inferred from latency. Load testing moves to replaying real peak traffic,
which is what would have caught this. And the runbook gets a resource-limits
section, because the current one describes a service that fails in ways this
one does not.
