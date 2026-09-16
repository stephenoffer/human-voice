# Postmortem: Checkout Outage on March 4

## Executive Summary

On March 4, the checkout service experienced an outage that prevented a significant portion of customers from completing purchases. The incident was caused by a database connection pool exhaustion triggered by a configuration change. The team identified the issue, rolled back the change, and restored service. This postmortem describes what happened, why it happened, and what we are doing to prevent it from happening again.

## Impact

The outage had a meaningful impact on customers and on the business. Many customers who attempted to check out during the incident window were unable to complete their purchases, which led to frustration and a loss of trust. Some customers contacted support, increasing the load on the support team during an already busy period.

From a business perspective, the incident resulted in lost revenue and may have affected customer retention. The reputational impact is harder to measure but should not be underestimated, since reliability is a core expectation for any e-commerce experience. Internal teams were also affected, as engineers across several groups were pulled away from planned work to help with investigation and recovery.

Overall, the impact highlights the importance of a resilient checkout flow and the need for stronger safeguards around configuration changes that affect critical services.

## Timeline

- 14:02 UTC: PR #4812 merged, lowering `DB_POOL_MAX` from 80 to 20 in `checkout-api/config/prod.yaml`.
- 14:09 UTC: Argo CD syncs the change; 12 pods restart over 4 minutes.
- 14:13 UTC: `checkout_db_pool_wait_seconds` p99 rises from 0.02 to 9.8.
- 14:16 UTC: PagerDuty fires `CheckoutErrorRateHigh` (5xx at 31%).
- 14:24 UTC: On-call identifies pool saturation from `pg_stat_activity`.
- 14:31 UTC: Revert merged as PR #4815.
- 14:38 UTC: All pods healthy; 5xx back under 0.2%.

## Root Cause

PR #4812 was intended for the staging overlay but edited the production file. With `DB_POOL_MAX=20` and 12 pods, the service could hold at most 240 connections, while peak traffic needed roughly 610. Requests queued on `pool.acquire()` with a 10-second timeout, and the upstream gateway timed out at 8 seconds, so most failures surfaced as 504s before the pool timeout ever fired. The config linter checks types but not value ranges, and the PR had one approval from a reviewer outside the payments team.

## Detection

Detection worked as expected.

## Communication

The status page was updated.

## Lessons Learned

We learned that configuration changes to critical services need stronger safeguards. A database connection pool exhaustion triggered by a configuration change caused the checkout outage, preventing customers from completing purchases. Reliability is a core expectation for any e-commerce experience, and the team will continue to invest in resilient checkout flows.

## Action Items

- Add range validation for pool settings to the config linter.
- Require payments-team approval for `checkout-api/config/prod.yaml`.
- Alert on `checkout_db_pool_wait_seconds` p99 above 1 second.
