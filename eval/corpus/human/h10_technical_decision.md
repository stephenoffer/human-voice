# We're staying on the monolith

The team voted to keep the monolith and not break it into services, and I want to write down why so we stop relitigating it every quarter.

We are nine engineers. The case for microservices is mostly about letting independent teams ship without coordinating. We do not have independent teams. We have one team that eats lunch together. Splitting the codebase would buy us deployment isolation we don't need and hand us a distributed-systems tax we can't afford: network calls where we had function calls, eventual consistency where we had a transaction, and a tracing setup nobody wants to maintain.

When we are forty engineers and the deploy queue is the bottleneck, this decision is wrong and we should revisit it. We are not there. Until the org chart forces the split, the monolith wins on every axis we actually care about today.
