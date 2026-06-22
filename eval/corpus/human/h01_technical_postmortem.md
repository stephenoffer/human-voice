# Why the queue backed up on Tuesday

At 14:07 the payments worker stopped draining its queue. Nobody noticed for eleven minutes because the dashboard averages over a five-minute window, so the spike looked like normal jitter until it didn't.

The cause was dumb. We'd shipped a retry loop that retried on a 4xx. Stripe returns 402 when a card is declined. A declined card is not a transient failure, but the loop treated it like one, so every decline became sixteen attempts spaced two seconds apart. Multiply that by the Tuesday afternoon volume and the workers spent all their time replaying doomed requests.

Fix was three lines: only retry on 5xx and 429. I added a metric for retry-per-request so next time the graph screams before the queue does. We still owe ourselves a real circuit breaker, but that's next sprint, not tonight.
