# Reducing cold-start latency in serverless functions

Cold starts remain the most common complaint about serverless architectures, and most of the mitigation advice online addresses symptoms rather than causes. The underlying issue is that your function's initialization cost is paid on a request that a user is waiting for.

Several factors contribute to initialization time:

- **Package size.** The runtime has to download and extract your deployment bundle. Trimming dependencies has a direct, measurable effect.
- **Runtime choice.** Interpreted runtimes generally start faster than JVM-based ones, though the gap has narrowed with ahead-of-time compilation options.
- **Connection setup.** Establishing a database connection during initialization is common and expensive, particularly when the connection requires a TLS handshake.
- **Configuration fetching.** Functions that pull secrets or feature flags at startup add a network round trip to every cold start.

The most effective single change is usually moving work out of the initialization path and making it lazy. A database connection established on first use rather than at import time costs the same, but the cost lands on a warm invocation more often than not.

Provisioned concurrency solves the problem directly by keeping instances warm, at a price. It makes sense for user-facing paths with predictable traffic and rarely makes sense for background processing.
