# Why we moved off the shared Postgres

After two years on a single Postgres 13 instance, my team decided to give the billing service its own database. I will explain the reasoning, because some colleagues still ask me about it in the corridor.

The shared instance was fine until last November. Then billing started running a nightly reconciliation job that scanned the whole invoices table. During that hour, the API for our analytics product slowed down badly. We measured p99 latency of 4.2 seconds, against a normal of 180 milliseconds. Customers noticed. Two of them opened tickets.

We considered tuning the query first. It helped a little. But the real problem was that two workloads with very different shapes were fighting for the same buffer cache.

So we split. Billing now lives on its own RDS instance, and the analytics database breathes again. The migration took three weekends, mostly because of foreign keys we had forgotten about. Was it worth the cost? For us, yes. The duplicated user data is annoying, and I keep an eye on it. But nobody has been paged at 2am since February, and that alone pays for the second instance.
